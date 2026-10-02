# Information, Scouting, and Recovery Behavioral Contract

## Purpose

Turn scouting into decision-grade information and make recovery preserve valid strategic intent.

## Information ownership

Information observes:

- map context;
- enemy composition;
- production signals;
- enemy infrastructure;
- exposed economy;
- water state;
- disconnected objectives;
- relic opportunity when proven.

Strategy interprets those observations.

## Scouting doctrine

A scout exists to answer a decision-changing question.

Examples:

- Is mounted pressure sustained?
- Is ranged pressure transitional?
- Has the opponent added production?
- Is a Castle/TC expansion happening?
- Is naval pressure emerging?
- Is the transport destination still valid?

A search result with no strategic consumer is not useful strategy coverage.

## DUC consumers

Named consumers include:

- composition scout;
- siege targeter;
- dock observer;
- naval targeter;
- transport destination reacquirer;
- tactical reacquisition consumer.

DUC SearchSession/TargetSession remains the execution substrate.

Target identity, search generation, filter generation, and liveness are not collapsed.

## Recovery doctrine

Every standing demand follows:

`loss -> reassess -> preserve intent if valid -> reopen execution`

Examples:

- lost provider -> reopen provider;
- resource starvation -> retain demand, release only lower-priority claims;
- military loss -> reopen replacement;
- failed construction -> retry/replan;
- lost transport -> preserve crossing objective;
- lost Monk package -> reopen support;
- changed enemy composition -> reassess package.

## Invalidation

Invalidation requires strategic evidence.

A timer firing, action failure, or temporary shortage is not invalidation.

## Acceptance

Tests must verify:

- information changes a consuming strategy state;
- DUC target provenance remains intact;
- failure preserves persistent demand;
- recovery reopens only when capability returns;
- obsolete objectives are explicitly released;
- fingerprints remain deterministic.
