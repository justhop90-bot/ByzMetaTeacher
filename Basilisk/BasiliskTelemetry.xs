// Basilisk telemetry consumer.
// The .per controller owns all policy and resource state.
// This XS function only drains the bounded event journal.
// AI-safe calls are limited to goal reads/writes, game time, and debug chat.

const int BT_DEBUG_VERBOSITY_GOAL = 700;

const int BT_TELEMETRY_READ_HEAD_GOAL = 739;
const int BT_TELEMETRY_COUNT_GOAL = 740;
const int BT_TELEMETRY_DROPPED_GOAL = 742;
const int BT_TELEMETRY_OVERFLOW_GOAL = 743;

const int BT_SLOT0_TYPE = 753;
const int BT_SLOT0_FROM = 754;
const int BT_SLOT0_TO = 755;
const int BT_SLOT0_MODE = 756;
const int BT_SLOT0_REASON = 757;
const int BT_SLOT0_FLAGS = 758;
const int BT_SLOT0_TIME = 759;
const int BT_SLOT0_SEQUENCE = 760;

const int BT_SLOT1_TYPE = 761;
const int BT_SLOT1_FROM = 762;
const int BT_SLOT1_TO = 763;
const int BT_SLOT1_MODE = 764;
const int BT_SLOT1_REASON = 765;
const int BT_SLOT1_FLAGS = 766;
const int BT_SLOT1_TIME = 767;
const int BT_SLOT1_SEQUENCE = 768;

const int BT_SLOT2_TYPE = 769;
const int BT_SLOT2_FROM = 770;
const int BT_SLOT2_TO = 771;
const int BT_SLOT2_MODE = 772;
const int BT_SLOT2_REASON = 773;
const int BT_SLOT2_FLAGS = 774;
const int BT_SLOT2_TIME = 775;
const int BT_SLOT2_SEQUENCE = 776;

const int BT_SLOT3_TYPE = 777;
const int BT_SLOT3_FROM = 778;
const int BT_SLOT3_TO = 779;
const int BT_SLOT3_MODE = 780;
const int BT_SLOT3_REASON = 781;
const int BT_SLOT3_FLAGS = 782;
const int BT_SLOT3_TIME = 783;
const int BT_SLOT3_SEQUENCE = 784;

void bt_chat_event(int sequence, int time, int type, int fromOwner, int toOwner, int mode, int reason, int flags) {
    if(xsGetGoal(BT_DEBUG_VERBOSITY_GOAL) >= 1) {
        xsChatData("[BASILISK-PREEMPT] seq="+sequence+" time="+time+" type="+type+" from="+fromOwner+" to="+toOwner+" mode="+mode+" reason="+reason+" flags="+flags);
    }
}

void bt_read_slot(int slot) {
    int type = 0;
    int fromOwner = 0;
    int toOwner = 0;
    int mode = 0;
    int reason = 0;
    int flags = 0;
    int time = 0;
    int sequence = 0;

    if(slot == 0) {
        type = xsGetGoal(BT_SLOT0_TYPE);
        fromOwner = xsGetGoal(BT_SLOT0_FROM);
        toOwner = xsGetGoal(BT_SLOT0_TO);
        mode = xsGetGoal(BT_SLOT0_MODE);
        reason = xsGetGoal(BT_SLOT0_REASON);
        flags = xsGetGoal(BT_SLOT0_FLAGS);
        time = xsGetGoal(BT_SLOT0_TIME);
        sequence = xsGetGoal(BT_SLOT0_SEQUENCE);
        xsSetGoal(BT_SLOT0_TYPE, 0);
        xsSetGoal(BT_SLOT0_FROM, 0);
        xsSetGoal(BT_SLOT0_TO, 0);
        xsSetGoal(BT_SLOT0_MODE, 0);
        xsSetGoal(BT_SLOT0_REASON, 0);
        xsSetGoal(BT_SLOT0_FLAGS, 0);
        xsSetGoal(BT_SLOT0_TIME, 0);
        xsSetGoal(BT_SLOT0_SEQUENCE, 0);
    } else if(slot == 1) {
        type = xsGetGoal(BT_SLOT1_TYPE);
        fromOwner = xsGetGoal(BT_SLOT1_FROM);
        toOwner = xsGetGoal(BT_SLOT1_TO);
        mode = xsGetGoal(BT_SLOT1_MODE);
        reason = xsGetGoal(BT_SLOT1_REASON);
        flags = xsGetGoal(BT_SLOT1_FLAGS);
        time = xsGetGoal(BT_SLOT1_TIME);
        sequence = xsGetGoal(BT_SLOT1_SEQUENCE);
        xsSetGoal(BT_SLOT1_TYPE, 0);
        xsSetGoal(BT_SLOT1_FROM, 0);
        xsSetGoal(BT_SLOT1_TO, 0);
        xsSetGoal(BT_SLOT1_MODE, 0);
        xsSetGoal(BT_SLOT1_REASON, 0);
        xsSetGoal(BT_SLOT1_FLAGS, 0);
        xsSetGoal(BT_SLOT1_TIME, 0);
        xsSetGoal(BT_SLOT1_SEQUENCE, 0);
    } else if(slot == 2) {
        type = xsGetGoal(BT_SLOT2_TYPE);
        fromOwner = xsGetGoal(BT_SLOT2_FROM);
        toOwner = xsGetGoal(BT_SLOT2_TO);
        mode = xsGetGoal(BT_SLOT2_MODE);
        reason = xsGetGoal(BT_SLOT2_REASON);
        flags = xsGetGoal(BT_SLOT2_FLAGS);
        time = xsGetGoal(BT_SLOT2_TIME);
        sequence = xsGetGoal(BT_SLOT2_SEQUENCE);
        xsSetGoal(BT_SLOT2_TYPE, 0);
        xsSetGoal(BT_SLOT2_FROM, 0);
        xsSetGoal(BT_SLOT2_TO, 0);
        xsSetGoal(BT_SLOT2_MODE, 0);
        xsSetGoal(BT_SLOT2_REASON, 0);
        xsSetGoal(BT_SLOT2_FLAGS, 0);
        xsSetGoal(BT_SLOT2_TIME, 0);
        xsSetGoal(BT_SLOT2_SEQUENCE, 0);
    } else {
        type = xsGetGoal(BT_SLOT3_TYPE);
        fromOwner = xsGetGoal(BT_SLOT3_FROM);
        toOwner = xsGetGoal(BT_SLOT3_TO);
        mode = xsGetGoal(BT_SLOT3_MODE);
        reason = xsGetGoal(BT_SLOT3_REASON);
        flags = xsGetGoal(BT_SLOT3_FLAGS);
        time = xsGetGoal(BT_SLOT3_TIME);
        sequence = xsGetGoal(BT_SLOT3_SEQUENCE);
        xsSetGoal(BT_SLOT3_TYPE, 0);
        xsSetGoal(BT_SLOT3_FROM, 0);
        xsSetGoal(BT_SLOT3_TO, 0);
        xsSetGoal(BT_SLOT3_MODE, 0);
        xsSetGoal(BT_SLOT3_REASON, 0);
        xsSetGoal(BT_SLOT3_FLAGS, 0);
        xsSetGoal(BT_SLOT3_TIME, 0);
        xsSetGoal(BT_SLOT3_SEQUENCE, 0);
    }

    bt_chat_event(sequence, time, type, fromOwner, toOwner, mode, reason, flags);
}

void bt_telemetry_drain() {
    int readHead = xsGetGoal(BT_TELEMETRY_READ_HEAD_GOAL);
    int count = xsGetGoal(BT_TELEMETRY_COUNT_GOAL);
    int drained = 0;

    while(count > 0 && drained < 4) {
        bt_read_slot(readHead);
        readHead = readHead + 1;
        if(readHead >= 4)
            readHead = 0;
        count = count - 1;
        drained = drained + 1;
    }

    xsSetGoal(BT_TELEMETRY_READ_HEAD_GOAL, readHead);
    xsSetGoal(BT_TELEMETRY_COUNT_GOAL, count);

    int dropped = xsGetGoal(BT_TELEMETRY_DROPPED_GOAL);
    int overflow = xsGetGoal(BT_TELEMETRY_OVERFLOW_GOAL);
    if(overflow != 0 && xsGetGoal(BT_DEBUG_VERBOSITY_GOAL) >= 1) {
        xsChatData("[BASILISK-PREEMPT] telemetry-overflow dropped="+dropped);
    }
    if(overflow != 0) {
        xsSetGoal(BT_TELEMETRY_DROPPED_GOAL, 0);
        xsSetGoal(BT_TELEMETRY_OVERFLOW_GOAL, 0);
    }
}
