#include "telemetry_queue.h"

#include <string.h>

#define RETRY_BASE_MS 1000UL
#define RETRY_MAX_MS 30000UL

void telemetry_queue_init(telemetry_queue_t *queue) {
    memset(queue, 0, sizeof(*queue));
}

bool telemetry_queue_push(telemetry_queue_t *queue, const char *payload) {
    if (queue->count >= TELEMETRY_QUEUE_CAPACITY) {
        return false;
    }

    telemetry_item_t *item = &queue->items[queue->tail];
    strncpy(item->payload, payload, TELEMETRY_PAYLOAD_MAX - 1);
    item->payload[TELEMETRY_PAYLOAD_MAX - 1] = '\0';
    item->next_attempt_ms = 0;
    item->attempts = 0;

    queue->tail = (queue->tail + 1) % TELEMETRY_QUEUE_CAPACITY;
    queue->count++;
    return true;
}

bool telemetry_queue_peek(telemetry_queue_t *queue, telemetry_item_t **item) {
    if (queue->count == 0) {
        return false;
    }
    *item = &queue->items[queue->head];
    return true;
}

void telemetry_queue_pop(telemetry_queue_t *queue) {
    if (queue->count == 0) {
        return;
    }
    queue->head = (queue->head + 1) % TELEMETRY_QUEUE_CAPACITY;
    queue->count--;
}

void telemetry_queue_schedule_retry(telemetry_item_t *item, unsigned long now_ms) {
    unsigned long delay = RETRY_BASE_MS << item->attempts;
    if (delay > RETRY_MAX_MS) {
        delay = RETRY_MAX_MS;
    }
    item->attempts++;
    item->next_attempt_ms = now_ms + delay;
}

size_t telemetry_queue_count(const telemetry_queue_t *queue) {
    return queue->count;
}
