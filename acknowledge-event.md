# `acknowledge-event`

[All symbols](../ai-symbol-reference.md)

<a id="symbol-acknowledge-event"></a>

## `acknowledge-event`

- Kind: `command`
- Detail: Action - Scenarios

Syntax: `(acknowledge-event <EventType> <EventId>)`

Acknowledges a received event by resetting the associated flag. Scenario triggers that execute an AI Script Goal effect are the only events that AI scripts can detect. This command, along with event-detected, is used to detect an AI Script Goal effect from a scenario trigger, often with the intention of changing the AI behavior after the scenario trigger has fired. The scenario designer chooses an AI Trigger number for the AI Script Goal effect in the scenario editor. Then, the event-detected command in the AI script will detect when this trigger effect happens. The event-detected command will remain true after the AI Script Goal trigger effect fires, so acknowledge-event is used to reset the event-detected flag so that event-detected will no longer be true, similar to how the disable-timer command clears a timer that has triggered or how the acknowledge-taunt" command accepts the taunt message." cAcknowledgeEvent.commandParameters = [ { nameLink: pEventType.getLink(), name: "EventType", type: "Const", dir: "in", range: "trigger", note: "The type of the event. Triggers are the only valid event types." }, { nameLink: pEventId.getLink(), name: "EventId", type: "Const", dir: "in", range: "0 to 255.", note: "The EventId to acknowledge." } ]

[AIRef](https://airef.github.io/commands/commands-details.html#acknowledge-event)

Completion insert text:

```text
(acknowledge-event ${1:EventType} ${2:EventId})
```

