#ifndef TELEMETRY_QUEUE_H
#define TELEMETRY_QUEUE_H

#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define TELEMETRY_QUEUE_CAPACITY 8
#define TELEMETRY_PAYLOAD_MAX 256

typedef struct {
    char payload[TELEMETRY_PAYLOAD_MAX];
    unsigned long next_attempt_ms;
    unsigned char attempts;
} telemetry_item_t;

typedef struct {
    telemetry_item_t items[TELEMETRY_QUEUE_CAPACITY];
    size_t head;
    size_t tail;
    size_t count;
} telemetry_queue_t;

void telemetry_queue_init(telemetry_queue_t *queue);
bool telemetry_queue_push(telemetry_queue_t *queue, const char *payload);
bool telemetry_queue_peek(telemetry_queue_t *queue, telemetry_item_t **item);
void telemetry_queue_pop(telemetry_queue_t *queue);
void telemetry_queue_schedule_retry(telemetry_item_t *item, unsigned long now_ms);
size_t telemetry_queue_count(const telemetry_queue_t *queue);

#ifdef __cplusplus
}
#endif

#endif
