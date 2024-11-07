"""
Run ranging_survey_from_obsfile.py for several stations in sequence.
CLI inputs to be read from a CSV or JSON file (sole input argument here).
"""
import argparse
import numpy as np
import pandas as pd
import os
import subprocess
