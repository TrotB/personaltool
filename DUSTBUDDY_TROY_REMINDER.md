# DustBuddy Troy Work Reminder

This workspace does not currently contain the DustBuddy Troy trading code. It is the
`TrotB/personaltool` Statement Markup Tool repository, so the trading-mode changes
cannot be implemented here without the correct repo or local PC files.

## Do this when back at the PC

1. Open the DustBuddy Troy trading repository/project.
2. Start a new coding agent from that repo, or paste this checklist into the agent.
3. Ask the agent to implement and test the items below.

## Required DustBuddy Troy changes

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
- Add an audit system to track whether strategies are decaying over time so the bot
  can keep a consistent edge.

## Suggested audit-system behavior

Track performance by strategy and mode over rolling windows, including:

- Win rate
- Profit factor
- Average R multiple or average expectancy
- Max drawdown
- Number of trades in the sample
- Date/time of last trade
- Whether the strategy is active, under review, or disabled

Flag or disable strategies when recent performance falls below configured thresholds
after a minimum sample size. Keep the thresholds configurable per strategy/mode.

## Prompt to use in the correct repo

```text
Implement DustBuddy Troy support for Lucid 25k Flex Eval and Lucid 50k Flex Eval
trading modes. Use the existing mode/risk-rule architecture. Add callout caps of 750
for 25k Flex Eval and 1500 for all 50k eval accounts. Keep swing trading test mode
free of these eval-specific restrictions for now. Add a strategy audit system that
tracks strategy performance over rolling windows and flags strategies whose edge is
decaying over time. Include focused tests for mode selection, callout caps, swing mode
behavior, and strategy audit state changes.
```
