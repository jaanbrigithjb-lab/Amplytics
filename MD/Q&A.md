
# <-------> EDA — Exploratory Data Analysis:
# Q: What is EDA, and how did you do it in this project?
    
    Answer: “EDA is examining the data before modeling: understanding where it came from, its size and fields, data # quality, and patterns. This project has no separate EDA notebook or chart-generation script. I can # show the dataset metadat 
    a and the conversion script to explain the source, reported dataset size, and transformations. I would not claim this project generates EDA charts.”

# Show: [dataset_metadata.json](</home/money_d_luffy/Desktop/Python Development/Amplytics/data/raw/dataset_metadata.json>:2) identifies the source; [dataset_metadata.json](</home/money_d_luffy/Desktop/Python Development/Amplytics/data/raw/dataset_metadata.json>:7) reports dataset counts.

Explanation: The metadata reports UCI Electricity Load Diagrams, 100 households, 3,475 billing periods, and 102,752 daily rows. It is a concise dataset summary, but not a full exploratory analysis with plots or distributions.

# Q: How are the original readings converted into daily electricity usage?
    
    Answer: “The source readings are 15-minute average power in kW. The converter resamples by day, sums the intervals, multiplies by 0.25 hours per interval, and rounds the result to get daily kWh.”

# Show: [convert_uci_load_diagrams.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/scripts/convert_uci_load_diagrams.py>:54) reads and resamples; [convert_uci_load_diagrams.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/scripts/convert_uci_load_diagrams.py>:61) applies the conversion.

# Q: Are target units and target-exceeded labels directly supplied by the source?
    
    Answer: “No. In this conversion path, target units are derived from previous-period usage using a bounded random factor. The target-exceeded label is then derived by comparing final usage with the target. That means the label is not an independently measured utility outcome, and the limitation should be disclosed.”

# Show: [convert_uci_load_diagrams.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/scripts/convert_uci_load_diagrams.py>:97) and [convert_uci_load_diagrams.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/scripts/convert_uci_load_diagrams.py>:98); [dataset_metadata.json](</home/money_d_luffy/Desktop/Python Development/Amplytics/data/raw/dataset_metadata.json>:16) lists derived fields and [dataset_metadata.json](</home/money_d_luffy/Desktop/Python Development/Amplytics/data/raw/dataset_metadata.json>:23) documents limitations.




# <-------> Data preprocessing and feature construction:
# Q: Which file prepares data for the models?
    
    Answer: “scripts/build_training_data.py reads billing and daily-consumption CSVs, converts date columns, groups readings by billing period, creates time-based snapshots, adds the training outcomes, and writes the processed training CSV.”

# Show: [build_training_data.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/scripts/build_training_data.py>:20) starts the process; [build_training_data.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/scripts/build_training_data.py>:21) reads the raw CSVs; [build_training_data.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/scripts/build_training_data.py>:27) converts date fields; [build_training_data.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/scripts/build_training_data.py>:31) groups records; [build_training_data.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/scripts/build_training_data.py>:79) saves processed data.

# Q: What is a prediction snapshot?
    
    Answer: “A snapshot is the information available at one point during a billing period. The project makes snapshots at about 25%, 50%, 75%, and 90% through the period, so it can train on predictions made before the period ends.”

# Show: [build_training_data.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/scripts/build_training_data.py>:17) defines those fractions; [build_training_data.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/scripts/build_training_data.py>:56) iterates through them.

# Q: How do you avoid using future information in the model inputs?
    
    Answer: “For each snapshot, build_snapshot only includes consumption records dated on or before the prediction date. The final usage and target-exceeded outcome are labels for learning/evaluation, not among the configured input features.”

# Show: [features.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/features.py>:21) applies the date cutoff; [build_training_data.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/scripts/build_training_data.py>:72) attaches final usage; [build_training_data.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/scripts/build_training_data.py>:73) derives the classification label; [config.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/config.py>:18) lists model features.

# Q: What features are used?
    
    Answer: “The seven features are target units, period days, elapsed days, days remaining, cumulative units, average daily units, and previous-period units.”

# Show: [config.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/config.py>:18). The snapshot values are assembled in [features.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/features.py>:34).

# Q: How are missing values and differing feature scales handled?
    
    Answer: “Each model uses a pipeline that fills missing feature values with the median, standardizes feature scales, and then fits the estimator. The pipeline is fit on training data, helping prevent the test data from influencing preprocessing.”

# Show: Regression pipeline: [train_models.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/scripts/train_models.py>:34). Classification pipeline: [train_models.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/scripts/train_models.py>:42).

# Q: How do you split training and test data?
    
    Answer: “The script uses a 25% test split grouped by billing period. Each period has multiple snapshots, so grouping helps keep snapshots from the same period on one side of the split rather than distributing related rows across training and testing.”

# Show: [train_models.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/scripts/train_models.py>:55).




# <-------> Linear regression:
# Q: What does the linear regression model predict?
    
    Answer: It predicts a continuous numeric value: actual_final_units, the final usage for a billing period. The model learns from the seven features.

Where to # show: [train_models.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/scripts/train_models.py>:61) fits it; [train_models.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/scripts/train_models.py>:62) predicts test values.

# Q: How do you measure regression performance?
    
    Answer: The project reports MAE and RMSE. MAE is the average absolute difference between predicted and actual usage. RMSE also measures prediction error, but penalizes larger errors more strongly.

Where to # show: [train_models.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/scripts/train_models.py>:63).

# Q: Is there a baseline comparison?
    
    Answer: Yes. The baseline multiplies average daily usage by the total number of period days, then evaluates that estimate using MAE and RMSE. This checks whether the ML regression model improves on a simple projection.

Where to # show: [train_models.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/scripts/train_models.py>:67).




# <-------> Logistic regression:
# Q: What does logistic regression predict?
    
    Answer: It predicts a binary outcome: whether final usage exceeds the target. The model is trained with target_exceeded; it estimates a probability, then the training evaluation uses a 0.5 threshold to assign class 0 or 1.

Where to # show: [train_models.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/scripts/train_models.py>:73) fits the classifier; [train_models.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/scripts/train_models.py>:74) calculates probabilities; [train_models.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/scripts/train_models.py>:75) applies the threshold.

# Q: What classification metrics are used?
    
    Answer: Precision, recall, F1, and a confusion matrix. Precision describes how many predicted exceedances were correct; recall describes how many actual exceedances the model detected; F1 balances precision and recall.

Where to # show: [train_models.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/scripts/train_models.py>:77).

# Q: Is the training threshold the same as the app warning threshold?
    
    Answer: No. Training evaluation uses 0.5. The app’s warning threshold is separately set to 0.70, so don’t confuse the two.

Where to # show: [train_models.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/scripts/train_models.py>:75) and [config.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/config.py>:30).




# <-------> Why linear regression and logistic regression?
# Q: Many models are available. Why did you choose these two?
    
    Answer: “The project needs to answer two different # questions. Linear regression estimates a numeric final electricity usage, while logistic regression estimates the probability  
     of a binary outcome—whether usage exceeds the target. They are established, relatively simple baseline models that train # quickly and are straightforward to explain in a prototype. Logistic regression also gives a probability that can be used for a wa 
    rning. The project code # shows these choices, but it does not document a formal comparison proving they are the best possible models.”

Explain the distinction: The models are selected because the project has one continuous target and one yes/no target—not because the two algorithms are interchangeable. Linear regression predicts a number; logistic regression predicts a class probability.

# Show: The estimator choices are in [train_models.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/scripts/train_models.py>:34) and [train_models.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/scripts/train_models.py>:42). The two training targets are visible at [train_models.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/scripts/train_models.py>:61) and [train_models.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/scripts/train_models.py>:73).

# Q: Why not use a more complex model such as a random forest or neural network?
    
    Answer: “A more complex model could be evaluated later, but it is not automatically better. For this prototype, simple models provide a clear baseline, are # quick to train, and are easier to explain. A fair decision would compare candidate models on the same grouped test split and me   
    trics, then select based on test performance and project needs. This project does not include that broad model comparison, so I should not claim these models were proven superior.”

# Q: Why use linear regression for final consumption?
    
    Answer: “Final consumption is a continuous numeric value, so regression is appropriate. The model learns a relationship between the seven snapshot features and actual_final_units.”

# Show: [train_models.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/scripts/train_models.py>:61) fits the regressor; [train_models.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/scripts/train_models.py>:62) predicts test usage.

# Q: Why use logistic regression for target exceedance?
    
    Answer: “Target exceedance is binary: exceeded or not exceeded. Logistic regression is appropriate for estimating the probability of that binary outcome. The script converts the probability into a 0/1 prediction using a 0.5 threshold for its reported evaluation.”

# Show: [train_models.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/scripts/train_models.py>:73) fits the classifier; [train_models.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/scripts/train_models.py>:74) calculates probabilities; [train_models.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/scripts/train_models.py>:75) applies the evaluation threshold.

# Q: How are the models evaluated?
    
    Answer: “Regression uses MAE and RMSE. Classification uses precision, recall, F1, and a confusion matrix. I use both error-based regression metrics and class-based classification metrics because the tasks have different kinds of outputs.”

# Show: Regression metrics: [train_models.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/scripts/train_models.py>:63). Classifier metrics: [train_models.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/scripts/train_models.py>:77).

# Q: Is the logistic evaluation threshold also the app’s warning threshold?
    
    Answer: “No. The training script uses 0.5 to calculate its evaluation predictions. The app warning threshold is separately configured as 0.70.”

# Show: [train_models.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/scripts/train_models.py>:75) and [config.py](</home/money_d_luffy/Desktop/Python Development/Amplytics/config.py>:30).

# Q: Does linear regression beat the simple baseline?
    
    Answer: “Not in the currently saved model metadata. The saved linear regression MAE/RMSE are approximately 3,173/8,169, while the baseline MAE/RMSE are approximately 2,159/6,184. Lower is better, so the baseline performed better in that saved run. That is important to report honestly; it suggests the regression model needs further evaluation or improvement.”

# Show: [model_metadata.json](</home/money_d_luffy/Desktop/Python Development/Amplytics/models/model_metadata.json>:19) and [model_metadata.json](</home/money_d_luffy/Desktop/Python Development/Amplytics/models/model_metadata.json>:23). Values may differ after retraining.