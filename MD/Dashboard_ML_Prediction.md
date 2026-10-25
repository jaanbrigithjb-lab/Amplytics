# On the dashboard, the ML prediction card shows two outputs from saved models, based on the chosen date’s data snapshot:

# Predicted final units (kWh): The Linear Regression model estimates total consumption for the end of the billing period. It uses target units, period length, days elapsed/remaining, cumulative units through the selected date, average daily use so far, and previous-period units. The result is clipped to zero if the model returns a negative value. See the feature order in config.py, how the dashboard builds the inputs in pages.py, and prediction handling in model_loader.py.

# Exceedance probability (%): The Logistic Regression model estimates the probability that final consumption will exceed the household target. The dashboard displays the model’s positive-class probability as a percentage; it is a target-exceedance risk, not a bill amount or certainty. See model_loader.py and the display in dashboard.html.
# The dashboard uses recorded and filled-in consumption through the selected date to form its snapshot. It does not feed future-period consumption into these inputs. Missing-day fill behavior is in pages.py, while the summary computes cumulative and average usage in calculations.py.

# The ML estimate is different from the adjacent Baseline projection, which uses average daily consumption × billing-period days. The displayed projected final energy charge is currently calculated from that baseline projection, not from ml_final. The dashboard template presents those separately in dashboard.html.

# The models are trained separately on saved training data, against actual final period units and a target-exceeded label; adding a user record does not retrain them. The repository states that this data is synthetic, so these outputs are estimates and their apparent accuracy should not be treated as real-world validation. See train_models.py and README.md.

