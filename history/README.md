# Cloud Sizes History

This directory includes a history of the data files from the different cloud providers.

Technically it's possible to pull this history from Git.  Hopefully a second copy here makes it easy to parse if you want to run any scripts on the historical data.  The layout should be fairly self-explanatory.

The Python script here, `pull_out_history.py`, will run on a clone of this repo and create individual files from the git history for this repo of the data files for the year in progress that's not yet checked into this folder.  The script `show_history.py` is an example script showing how to pull out each file from in and out of the tar files and process it in turn.
