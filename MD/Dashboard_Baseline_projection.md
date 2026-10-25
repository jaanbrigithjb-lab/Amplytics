# The dashboard’s Baseline projection estimates end-of-period consumption using:

# Baseline projected units = (cumulative units through the selected date ÷ elapsed days) × total billing-period days

# For example, if usage through the selected date is 113.23 kWh after 10 days in a 30-day period, the average is 11.323 kWh/day and the baseline projection is 339.69 kWh. The calculation is in calculate_summary.

# The selected date comes from the dashboard date picker. Missing days up to that date may be filled with estimated/predicted daily usage before the cumulative total is calculated; future days are not included in that running average. See the fill and summary steps in pages.py.

# The card also shows a projected final energy charge, calculated by applying the tariff calculator to the baseline’s projected units. It is separate from the ML prediction card. This is an estimate based on the current average, not a guaranteed final reading.