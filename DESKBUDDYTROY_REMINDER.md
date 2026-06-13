# DeskBuddyTroy Work Reminder

This workspace does not currently contain the DeskBuddyTroy trading code. It is the
`TrotB/personaltool` Statement Markup Tool repository, so the trading-mode changes
cannot be implemented here without the correct repo or local PC files.

## Do this when back at the PC

1. Open the DeskBuddyTroy trading repository/project.
2. Start a new coding agent from that repo, or paste this checklist into the agent.
3. Ask the agent to implement and test the items below.

## Required DeskBuddyTroy changes

- Add two new trading modes tied to Lucid Flex Eval rules:
  - Lucid 25k Flex Eval
  - Lucid 50k Flex Eval
- The new modes should use the Lucid Flex Eval risk/rule set used by those account
  sizes.
- Swing trading can continue to be tested without these eval-specific rules for now.
- Future/related callout sizing must be capped to the right eval account:
  - 25k Flex Eval: cap callout at 750
  - 50k Flex Eval: cap callout at 1500
  - All 50k eval modes/accounts should use the 1500 cap unless a more specific rule
    exists in the trading code.
- Add a strategy defense/audit system so every strategy is protected against alpha
  decay, overuse, market-regime mismatch, crowding, slippage, correlation risk, and
  other conditions that can kill an edge.

## Required strategy defense behavior

Every strategy should have a defensive health layer before it is allowed to keep
issuing callouts. Track performance by strategy, symbol, timeframe, mode, session,
and market regime over rolling windows, including:

- Win rate
- Profit factor
- Average R multiple or average expectancy
- Max drawdown
- Number of trades in the sample
- Date/time of last trade
- Slippage and fill quality
- Average adverse excursion and average favorable excursion
- Consecutive wins/losses
- Signal frequency versus normal baseline
- Correlation with other active strategies
- Whether the strategy is active, cooling down, reduced size, under review, or disabled

Defend against strategy failure modes with configurable rules:

- Alpha decay: compare recent expectancy, win rate, and profit factor against longer
  baselines after a minimum sample size.
- Overuse/crowding: throttle or cool down a strategy when signal frequency, repeated
  setup use, or same-direction exposure rises beyond normal ranges.
- Market regime mismatch: detect when volatility, trend/chop, volume, spread, session,
  or news conditions differ from the environment where the strategy works.
- Execution decay: flag a strategy when slippage, rejected orders, spread expansion,
  or late fills erode expected edge.
- Drawdown and loss streaks: reduce size, pause, or disable when drawdown or loss
  streak limits are breached.
- Correlation stacking: avoid multiple strategies taking effectively the same risk
  at the same time.
- Data quality: block signals when required market data, indicator data, fills, or
  trade logs are stale or incomplete.

Each strategy should expose a health state:

- `active`: normal callouts allowed.
- `reduced_size`: edge is weakening, but not fully invalidated.
- `cooldown`: temporarily pause after overuse, volatility shock, or loss streak.
- `under_review`: enough evidence suggests the edge may be decaying.
- `disabled`: no callouts until manually reviewed or reset by explicit rules.

The bot should log why a strategy changes state and include enough metrics to explain
the decision. Thresholds should be configurable per strategy/mode so good strategies
are not killed by one-size-fits-all rules.

## Prompt to use in the correct repo

```text
Implement DeskBuddyTroy support for Lucid 25k Flex Eval and Lucid 50k Flex Eval
trading modes. Use the existing mode/risk-rule architecture. Add callout caps of 750
for 25k Flex Eval and 1500 for all 50k eval accounts. Keep swing trading test mode
free of these eval-specific restrictions for now. Add a defensive strategy audit
system for every strategy that tracks rolling performance, alpha decay, overuse,
market-regime mismatch, execution/slippage decay, drawdown/loss streaks, correlation
stacking, and data-quality problems. Strategies should have health states such as
active, reduced_size, cooldown, under_review, and disabled, and the bot should log why
state changes happen. Include focused tests for mode selection, callout caps, swing
mode behavior, audit metrics, overuse throttling, decay detection, and strategy audit
state changes.
```
