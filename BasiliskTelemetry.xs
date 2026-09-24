// BASILISK bounded preemption telemetry consumer
// Loaded by Basilisk.per and called explicitly once per second.
// This layer observes telemetry only. It never owns strategy or resources.

const int BT_DEBUG_VERBOSITY = 700;
const int BT_RING_READ = 736;
const int BT_RING_COUNT = 737;
const int BT_RING_OVERFLOW = 739;
const int BT_RING_OVERFLOW_STATE = 740;
const int BT_SLOT_EVENT_BASE = 747;
const int BT_SLOT_OWNER_BASE = 751;
const int BT_SLOT_FLAGS_BASE = 755;
const int BT_SLOT_TIME_BASE = 759;
const int BT_SLOT_SEQUENCE_BASE = 763;

string basiliskTelemetryEventName(int eventType) {
    if(eventType == 1) return("PREEMPT-BEGIN");
    if(eventType == 2) return("DEFENSIVE-COUNTER");
    if(eventType == 3) return("PREEMPT-END");
    return("UNKNOWN");
}

void basiliskTelemetryDrain() {
    int readHead = xsGetGoal(BT_RING_READ);
    int count = xsGetGoal(BT_RING_COUNT);
    int processed = 0;

    while(count > 0 && processed < 4) {
        int eventType = xsGetGoal(BT_SLOT_EVENT_BASE + readHead);
        int owner = xsGetGoal(BT_SLOT_OWNER_BASE + readHead);
        int flags = xsGetGoal(BT_SLOT_FLAGS_BASE + readHead);
        int eventTime = xsGetGoal(BT_SLOT_TIME_BASE + readHead);
        int sequence = xsGetGoal(BT_SLOT_SEQUENCE_BASE + readHead);

        if(xsGetGoal(BT_DEBUG_VERBOSITY) >= 2) {
            xsChatData(
                "BASILISK | PREEMPT | event=" + basiliskTelemetryEventName(eventType) +
                " seq=" + sequence +
                " owner=" + owner +
                " flags=" + flags +
                " time=" + eventTime
            );
        }

        readHead = readHead + 1;
        if(readHead >= 4) readHead = 0;
        count = count - 1;

        xsSetGoal(BT_RING_READ, readHead);
        xsSetGoal(BT_RING_COUNT, count);
        processed = processed + 1;
    }

    if(xsGetGoal(BT_RING_OVERFLOW_STATE) > 0) {
        if(xsGetGoal(BT_DEBUG_VERBOSITY) >= 1) {
            xsChatData(
                "BASILISK | PREEMPT | FIFO-OVERFLOW count=" + xsGetGoal(BT_RING_OVERFLOW)
            );
        }
        xsSetGoal(BT_RING_OVERFLOW_STATE, 0);
    }
}
