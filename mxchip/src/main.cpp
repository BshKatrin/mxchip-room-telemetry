#include "telemetry_queue.h"

#include <Arduino.h>
#include <AZ3166WiFi.h>
#include <AZ3166WiFiClient.h>
#include <IoT_DevKit_HW.h>

#include <stdio.h>
#include <string.h>

#ifndef BACKEND_HOST
#define BACKEND_HOST "your-ec2-public-host-or-domain"
#endif

#ifndef BACKEND_PORT
#define BACKEND_PORT 8000
#endif

#ifndef BACKEND_PATH
#define BACKEND_PATH "/api/v1/telemetry"
#endif

#ifndef DEVICE_ID
#define DEVICE_ID "mxchip-devkit-01"
#endif

#define POST_PERIOD_MS 1800000UL
#define HTTP_RESPONSE_MAX 512

static telemetry_queue_t telemetry_queue;
static unsigned long last_sample_ms = 0;
static bool sample_taken = false;
static bool is_wifi_ready = false;
static UARTClass RustSerial(UART_1);

static void board_io_init(void);
static void log_line(const char *line);
static bool wifi_connect(void);
static bool http_post_json(const char *host, int port, const char *path, const char *json);
static bool rust_uart_read_line(char *buffer, size_t len);
static void sensor_payload(char *buffer, size_t len);
static int parse_http_status(const char *response);

void setup() {
    board_io_init();
    telemetry_queue_init(&telemetry_queue);

    log_line("mxchip telemetry boot");

    while (!wifi_connect()) {
        log_line("wifi connect failed; retry");
        delay(5000);
    }
}

void loop() {
    unsigned long now = millis();

    if (!sample_taken || now - last_sample_ms >= POST_PERIOD_MS) {
        char payload[TELEMETRY_PAYLOAD_MAX];
        if (!rust_uart_read_line(payload, sizeof(payload))) {
            sensor_payload(payload, sizeof(payload));
        }

        log_line("queue telemetry:");
        log_line(payload);

        if (!telemetry_queue_push(&telemetry_queue, payload)) {
            log_line("telemetry queue full; sample dropped");
        }
        last_sample_ms = now;
        sample_taken = true;
    }

    telemetry_item_t *item = NULL;
    if (telemetry_queue_peek(&telemetry_queue, &item) && now >= item->next_attempt_ms) {
        if (http_post_json(BACKEND_HOST, BACKEND_PORT, BACKEND_PATH, item->payload)) {
            telemetry_queue_pop(&telemetry_queue);
            log_line("telemetry posted");
        } else {
            telemetry_queue_schedule_retry(item, now);
            log_line("telemetry post failed; retry scheduled");
        }
    }

    delay(50);
}

static void board_io_init(void) {
    Serial.begin(115200);
    RustSerial.begin(115200);
    delay(1000);

    Screen.init();
    Screen.print(0, "Room telemetry");
    Screen.print(1, "Initializing...");

    int ret = initIoTDevKit(0);
    if (ret != 0) {
        Serial.print("initIoTDevKit failed: ");
        Serial.println(ret);
        Screen.print(1, "DevKit init failed");
    }
}

static void log_line(const char *line) {
    Serial.println(line);
}

static bool wifi_connect(void) {
    if (is_wifi_ready && WiFi.status() == WL_CONNECTED) {
        return true;
    }

    Screen.print(1, "Connecting WiFi");

#if defined(WIFI_SSID) && defined(WIFI_PASS)
    int status = WiFi.begin(WIFI_SSID, WIFI_PASS);
#else
    int status = WiFi.begin();
#endif

    if (status != WL_CONNECTED) {
        is_wifi_ready = false;
        Screen.print(2, "No WiFi");
        return false;
    }

    IPAddress ip = WiFi.localIP();
    char msg[64];
    snprintf(msg, sizeof(msg), "IP %s", ip.get_address());
    log_line(msg);
    Screen.print(1, msg);
    Screen.print(2, BACKEND_HOST);

    is_wifi_ready = true;
    return true;
}

static bool http_post_json(const char *host, int port, const char *path, const char *json) {
    WiFiClient client;
    char response[HTTP_RESPONSE_MAX];
    size_t response_len = 0;

    Serial.print("POST http://");
    Serial.print(host);
    Serial.print(":");
    Serial.print(port);
    Serial.println(path);

    if (!client.connect(host, (unsigned short)port)) {
        log_line("tcp connect failed");
        return false;
    }

    client.print("POST ");
    client.print(path);
    client.print(" HTTP/1.1\r\nHost: ");
    client.print(host);
    client.print(":");
    client.print(port);
    client.print("\r\nUser-Agent: mxchip-room-telemetry\r\nContent-Type: application/json\r\nConnection: close\r\nContent-Length: ");
    client.print((unsigned int)strlen(json));
    client.print("\r\n\r\n");
    client.print(json);

    unsigned long deadline = millis() + 5000;
    while (millis() < deadline && response_len + 1 < sizeof(response)) {
        int c = client.read();
        if (c < 0) {
            delay(10);
            continue;
        }
        response[response_len++] = (char)c;
        response[response_len] = '\0';
    }

    client.stop();

    int status = parse_http_status(response);
    Serial.print("http status: ");
    Serial.println(status);
    Serial.print("http response: ");
    Serial.println(response);

    return status >= 200 && status < 300;
}

static bool rust_uart_read_line(char *buffer, size_t len) {
    if (RustSerial.available() <= 0) {
        return false;
    }

    size_t pos = 0;
    unsigned long deadline = millis() + 100;
    while (millis() < deadline && pos + 1 < len) {
        if (RustSerial.available() <= 0) {
            delay(1);
            continue;
        }

        char c = (char)RustSerial.read();
        if (c == '\n') {
            break;
        }
        if (c != '\r') {
            buffer[pos++] = c;
        }
    }

    buffer[pos] = '\0';
    return pos > 0;
}

static void sensor_payload(char *buffer, size_t len) {
    float temperature = getDevKitTemperatureValue(0);
    float humidity = getDevKitHumidityValue();
    float pressure = getDevKitPressureValue();
    char pressure_field[48] = "";

    // Pressure is optional; an invalid sensor value must not reject the whole sample.
    if (pressure >= 300.0f && pressure <= 1200.0f) {
        snprintf(pressure_field, sizeof(pressure_field), ",\"pressure_hpa\":%.2f", pressure);
    } else {
        log_line("invalid pressure reading; omitting pressure_hpa");
    }

    snprintf(
        buffer,
        len,
        "{\"device_id\":\"%s\",\"temperature_c\":%.2f,\"humidity_percent\":%.2f%s}",
        DEVICE_ID,
        temperature,
        humidity,
        pressure_field
    );
}

static int parse_http_status(const char *response) {
    if (strncmp(response, "HTTP/", 5) != 0) {
        return 0;
    }

    const char *space = strchr(response, ' ');
    if (space == NULL) {
        return 0;
    }

    return atoi(space + 1);
}
