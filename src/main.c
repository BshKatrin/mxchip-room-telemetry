#include "telemetry_queue.h"

#include "stm32f4xx_hal.h"

#include <stdbool.h>
#include <stdio.h>
#include <string.h>

#define BACKEND_HOST "192.168.1.10"
#define BACKEND_PORT 8000
#define BACKEND_PATH "/api/v1/telemetry"
#define DEVICE_ID "mxchip-devkit-01"
#define POST_PERIOD_MS 5000UL

static telemetry_queue_t telemetry_queue;
static unsigned long last_sample_ms = 0;

static void SystemClock_Config(void);
static void board_io_init(void);
static void log_line(const char *line);
static bool wifi_connect(void);
static bool http_post_json(const char *host, int port, const char *path, const char *json);
static bool rust_uart_read_line(char *buffer, size_t len);
static void fallback_payload(char *buffer, size_t len);

int main(void) {
    HAL_Init();
    SystemClock_Config();
    board_io_init();
    telemetry_queue_init(&telemetry_queue);

    log_line("mxchip telemetry boot");

    while (!wifi_connect()) {
        log_line("wifi connect failed; retry");
        HAL_Delay(2000);
    }

    for (;;) {
        unsigned long now = HAL_GetTick();

        if (now - last_sample_ms >= POST_PERIOD_MS) {
            char payload[TELEMETRY_PAYLOAD_MAX];
            if (!rust_uart_read_line(payload, sizeof(payload))) {
                fallback_payload(payload, sizeof(payload));
            }

            if (!telemetry_queue_push(&telemetry_queue, payload)) {
                log_line("telemetry queue full; sample dropped");
            }
            last_sample_ms = now;
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

        HAL_Delay(50);
    }
}

static void SystemClock_Config(void) {
    /* Board-specific clock setup can be generated with STM32CubeMX later. */
}

static void board_io_init(void) {
    /* Init UART, Wi-Fi module, sensors here. Keep networking in C layer. */
}

static void log_line(const char *line) {
    (void)line;
}

static bool wifi_connect(void) {
    /* Replace with MXChip Wi-Fi driver call. */
    return true;
}

static bool http_post_json(const char *host, int port, const char *path, const char *json) {
    (void)host;
    (void)port;
    (void)path;
    (void)json;
    /* Replace with board HTTP client. Return true only after 2xx response. */
    return false;
}

static bool rust_uart_read_line(char *buffer, size_t len) {
    (void)buffer;
    (void)len;
    /* Read one newline-terminated JSON payload from Rust firmware over UART. */
    return false;
}

static void fallback_payload(char *buffer, size_t len) {
    snprintf(
        buffer,
        len,
        "{\"device_id\":\"%s\",\"temperature_c\":22.0,\"humidity_percent\":45.0}",
        DEVICE_ID
    );
}
