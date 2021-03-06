import numpy as np
from random import seed, shuffle
from sklearn.model_selection import KFold
from simpsons.functions import get_batches
from simpsons.helper import load_data, token_lookup, create_lookup_tables, \
    preprocess_and_save_data, load_preprocess
from hyperparameter_tuning_functions import generate_configs
from simpsons.model import RNN

K_FOLDS = 4

# Load data
data_dir = './data/simpsons/moes_tavern_lines.txt'
text = load_data(data_dir)

# Preprocess data
preprocess_and_save_data(data_dir, token_lookup, create_lookup_tables)

# Get pre-procesed data
int_text, vocab_to_int, int_to_vocab, token_dict = load_preprocess()

# Grid search of these parameters if performed
params_grid = {'num_epochs': [150],
               'batch_size': [200, 250],
               'rnn_size': [250, 500, 750],
               'embed_dim': [250],
               'seq_length': [10, 15],
               'learning_rate': [0.01, 0.005],
               'dropout_keep_prob': [0.9, 1.0],
               'lstm_layers': [2, 3, 4],
               'save_dir': ['./save']}

configs = generate_configs(params_grid)

# Keep track of best configuration
best_loss = np.inf
best_config = None

# Go through configs in random order
seed(0)
shuffle(configs)

for config in configs:
    print('')
    print('Running config:')
    print(config)

    # Get the batches of data.
    batches = get_batches(int_text, config)

    # Keep track of the validation losses.
    fold_val_losses = []

    # K-fold cross validation.
    # Batches has dims: num_batches x (input, target) x batch_size x seq_len
    kf = KFold(n_splits=K_FOLDS)

    for train_index, val_index in kf.split(batches):
        input_train, input_val = batches[train_index, 0, None, :, :], \
                                 batches[val_index, 0, None, :, :]
        target_train, target_val = batches[train_index, 1, None, :, :], \
                                   batches[val_index, 1, None, :, :]

        # RNN.train method expects the input and target data to be joined
        train_batches = np.concatenate((input_train, target_train), axis=1)
        val_batches = np.concatenate((input_val, target_val), axis=1)

        rnn = RNN(int_to_vocab, config)
        val_losses = rnn.train(config, train_batches, val_batches=val_batches)

        fold_val_losses.append(val_losses)

    # Find out the best num epochs for this config.
    # Array has same length as number of epochs.
    fold_avg_losses = np.array(fold_val_losses).mean(axis=0)

    config_best_loss = np.min(fold_avg_losses)

    # Loss from 1st epoch is stored at 0th index in fold_avg_losses
    config_best_num_epochs = np.argmin(fold_avg_losses) + 1

    if config_best_loss < best_loss:
        # New best loss
        best_loss = config_best_loss
        best_config = config
        best_config['num_epochs'] = config_best_num_epochs

    print('Best config so far:')
    print(best_config)
