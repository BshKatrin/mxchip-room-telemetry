#include "telemetry_queue.h"

#include <assert.h>
#include <string.h>

int main(void) {
    telemetry_queue_t queue;
    telemetry_queue_init(&queue);

    assert(telemetry_queue_push(&queue, "{\"device_id\":\"dev\"}"));
    assert(telemetry_queue_count(&queue) == 1);

    telemetry_item_t *item = NULL;
    assert(telemetry_queue_peek(&queue, &item));
    assert(strcmp(item->payload, "{\"device_id\":\"dev\"}") == 0);

    telemetry_queue_schedule_retry(item, 1000);
    assert(item->next_attempt_ms > 1000);

    telemetry_queue_pop(&queue);
    assert(telemetry_queue_count(&queue) == 0);
    return 0;
}
