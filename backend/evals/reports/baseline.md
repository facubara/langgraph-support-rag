# Eval report — `baseline`

Config overrides: `none (defaults)`

## Summary

| Metric | Score |
| --- | --- |
| n | 16 |
| task_success | 1.0 |
| intent_accuracy | 1.0 |
| tool_correctness | 1.0 |
| grounding_accuracy | 1.0 |
| action_correctness | 1.0 |
| policy_compliance | 1.0 |
| escalation_correctness | 1.0 |
| avg_latency_ms | 42.73 |
| total_cost_usd | 0.0 |

## Cases

| id | pass | intent | tools | grounding | action |
| --- | --- | --- | --- | --- | --- |
| dup_pro | ✅ | ✅ | ✅ | ✅ | ✅ |
| dup_pro_synonym | ✅ | ✅ | ✅ | ✅ | ✅ |
| dup_team_none | ✅ | ✅ | ✅ | ✅ | ✅ |
| dup_enterprise_review | ✅ | ✅ | ✅ | ✅ | ✅ |
| refund_pro | ✅ | ✅ | ✅ | ✅ | ✅ |
| refund_team | ✅ | ✅ | ✅ | ✅ | ✅ |
| refund_enterprise_escalate | ✅ | ✅ | ✅ | ✅ | ✅ |
| escalate_human_pro | ✅ | ✅ | ✅ | ✅ | ✅ |
| escalate_manager_team | ✅ | ✅ | ✅ | ✅ | ✅ |
| billing_latest_invoice | ✅ | ✅ | ✅ | ✅ | ✅ |
| billing_explain_charge | ✅ | ✅ | ✅ | ✅ | ✅ |
| faq_cancel | ✅ | ✅ | ✅ | ✅ | ✅ |
| faq_plans | ✅ | ✅ | ✅ | ✅ | ✅ |
| faq_refund_window | ✅ | ✅ | ✅ | ✅ | ✅ |
| offtopic_joke | ✅ | ✅ | ✅ | ✅ | ✅ |
| offtopic_capital | ✅ | ✅ | ✅ | ✅ | ✅ |
