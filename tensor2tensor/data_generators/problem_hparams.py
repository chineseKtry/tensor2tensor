# coding=utf-8
# Copyright 2017 The Tensor2Tensor Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Hyperparameters defining different problems.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os

# Dependency imports

from tensor2tensor.data_generators import text_encoder
from tensor2tensor.layers import modalities  # pylint: disable=unused-import
from tensor2tensor.utils import registry

import tensorflow as tf


def problem_hparams(problem_name, model_hparams):
  """Generate problem hyperparameters based on problem name.

  Args:
    problem_name: a string
    model_hparams: a tf.contrib.training.HParams

  Returns:
    a tf.contrib.training.HParams

  Raises:
    ValueError: if problem_name is unknown.
  """
  base_name, was_reversed, was_copy = parse_problem_name(problem_name)
  p = _lookup_problem_hparams_fn(base_name)(model_hparams)
  if was_reversed:
    _reverse_problem_hparams(p)
  if was_copy:
    _copy_problem_hparams(p)
  return p


def parse_problem_name(problem_name):
  """Determines if problem_name specifies a copy and/or reversal.

  Args:
    problem_name: A string containing a single problem name from FLAGS.problems.

  Returns:
    base_name: A string with the base problem name.
    was_reversed: A boolean.
    was_copy: A boolean.
  """
  # Recursively strip tags until we reach a base name.
  if problem_name.endswith("_rev"):
    base, _, was_copy = parse_problem_name(problem_name[:-4])
    return base, True, was_copy
  elif problem_name.endswith("_copy"):
    base, was_reversed, _ = parse_problem_name(problem_name[:-5])
    return base, was_reversed, True
  return problem_name, False, False


def _lookup_problem_hparams_fn(name):
  if name not in PROBLEM_HPARAMS_MAP:
    map_str = "* " + "\n* ".join(sorted(PROBLEM_HPARAMS_MAP.keys()))
    error_msg = "%s not in the supported set of problems:\n%s" % (name, map_str)
    raise ValueError(error_msg)
  return PROBLEM_HPARAMS_MAP.get(name)


def _copy_problem_hparams(p_hparams):
  """Use input modality, vocab, and space id for target."""
  p = p_hparams
  # Duplicate input modality.
  p.target_modality = p.input_modality["inputs"]
  # Duplicate input vocabulary.
  p.vocabulary["targets"] = p.vocabulary["inputs"]
  # Duplicate input space ids.
  p.target_space_id = p.input_space_id
  # Mark that p was reversed.
  p.was_copy = True


def _reverse_problem_hparams(p_hparams):
  """Swap input/output modalities, vocab, and space ids."""
  p = p_hparams

  # Swap modalities.
  input_modality = p.input_modality["inputs"]
  target_modality = p.target_modality
  p.input_modality["inputs"] = target_modality
  p.target_modality = input_modality

  # Swap vocabularies.
  input_vocabulary = p.vocabulary["inputs"]
  target_vocabulary = p.vocabulary["targets"]
  p.vocabulary["inputs"] = target_vocabulary
  p.vocabulary["targets"] = input_vocabulary

  # Swap input/target space ids.
  input_space_id = p.input_space_id
  target_space_id = p.target_space_id
  p.input_space_id = target_space_id
  p.target_space_id = input_space_id

  # Mark that p was reversed.
  p.was_reversed = True


def default_problem_hparams():
  """A set of basic model hyperparameters."""
  return tf.contrib.training.HParams(
      # Use this parameter to get comparable perplexity numbers with different
      # tokenizations.  This value should be set to the ratio of the number of
      # tokens in the test set according to the tokeization used to the number
      # of tokens in the test set in the "official" tokenization.  For example,
      # if we are using a word-piece based model and we want to compute
      # per-word perplexity, then we set loss_multiplier to the number of
      # wordpieces per word in the test set.
      loss_multiplier=1.0,

      # Use this parameter to allow for larger sequences in the batch. Without
      # the use of this parameter, the size of the inner two dimensions will be
      # used to judge the sequence length.
      batch_size_multiplier=1,

      # To make queues of the right capacity, it's good to know the maximal
      # expected batch size, as it can vary a lot. It only affects performance
      # of input readers and memory use. The defaults should be safe and fast,
      # but decrease if your reader uses a lot of memory and increase if slow.
      max_expected_batch_size_per_shard=64,

      # Modalities used to map from input features to a space compatible with
      # chosen model architecture.  One modality spec (which is a 2-tuple,
      # (modality_full_name, vocab_size)) per feature key. modality_full_name is
      # a string type:name, e.g. class_label:2d. Leaving off the name uses the
      # default modality for that type (e.g. class_label ==
      # class_label:default).
      input_modality={},

      # Modality used to map from hidden representation to the target space.
      # Specified as a modality spec, a 2-tuple described above.
      target_modality=None,

      # Identifiers used to tell the model which input/target space will be
      # expected. For example, it can tell that we expect French as characters
      # as output, or Spanish as sound. An integer with the following semantics:
      #   0: Generic / unknown output space (default)
      #   1: Image labels
      #   2: English characters
      #   3: English tokens
      #   4: English bpe tokens
      #   5: French characters
      #   6: French tokens
      #   7: German characters
      #   8: German tokens
      #   9: German bpe tokens
      #   10: Digit cipher lexicon 0
      #   11: Digit cipher lexicon 1
      #   12: Audio waveform domain
      #   13: Audio spectral domain
      #   14: Parse characters
      #   15: Parse tokens
      #   16: Chinese tokens
      #   17: Icelandic characters
      #   18: Icelandic tokens
      #   19: Icelandic parse tokens
      #   20: Macedonian tokens
      #   21: Czech tokens
      #   22: Czech characters
      # Add more above if needed.
      input_space_id=0,
      target_space_id=0,

      # Vocabulary per feature key.
      #   a vocabulary converts to/from human-readable strings.
      # E.g. {"inputs": text_encoder.ByteTextEncoder(),
      #       "targets": text_encoder.SubwordTextEncoder("vocab_filename.txt")}
      vocabulary={
          "inputs": text_encoder.TextEncoder(),
          "targets": text_encoder.TextEncoder()
      },

      # This is a marker to keep track if the problem was reversed or copied.
      # Only set automatically, do not override the default.
      #
      # These tags can be combined in order to perform copies of the input or
      # the targets. For instance `problem_copy` will copy the inputs, but
      # `problem_rev_copy` will copy the targets.
      was_reversed=False,
      was_copy=False,)


def test_problem_hparams(unused_model_hparams, input_vocab_size,
                         target_vocab_size):
  """Problem hparams for testing model bodies."""
  p = default_problem_hparams()
  p.input_modality = {"inputs": (registry.Modalities.SYMBOL, input_vocab_size)}
  p.target_modality = (registry.Modalities.SYMBOL, target_vocab_size)
  p.vocabulary = {
      "inputs": text_encoder.TextEncoder(),
      "targets": text_encoder.TextEncoder()
  }
  return p


def audio_timit_characters(unused_model_hparams):
  """English audio transcription benchmark."""
  p = default_problem_hparams()
  p.input_modality = {
      "inputs": (registry.Modalities.AUDIO, None),
  }
  p.target_modality = (registry.Modalities.SYMBOL, 256)
  p.vocabulary = {
      "inputs": text_encoder.TextEncoder(),
      "targets": text_encoder.ByteTextEncoder(),
  }
  p.batch_size_multiplier = 256
  p.loss_multiplier = 2.0
  p.input_space_id = 12
  p.target_space_id = 2
  return p


def audio_timit_tokens(model_hparams, wrong_vocab_size):
  """English audio transcription benchmark.

  Args:
    model_hparams: a tf.contrib.training.HParams
    wrong_vocab_size: a number used in the filename indicating the approximate
      vocabulary size.  This is not to be confused with the actual vocabulary
      size.
  Returns:
    a tf.contrib.training.HParams
  """
  p = default_problem_hparams()
  # This vocab file must be present within the data directory.
  vocab_filename = os.path.join(model_hparams.data_dir,
                                "vocab.endefr.%d" % wrong_vocab_size)
  subtokenizer = text_encoder.SubwordTextEncoder(vocab_filename)
  p.input_modality = {
      "inputs": (registry.Modalities.AUDIO, None),
  }
  p.target_modality = (registry.Modalities.SYMBOL, subtokenizer.vocab_size)
  p.vocabulary = {
      "inputs": text_encoder.TextEncoder(),
      "targets": subtokenizer,
  }
  p.batch_size_multiplier = 256
  p.loss_multiplier = 2.0
  p.input_space_id = 13
  p.target_space_id = 3
  return p


def wmt_parsing_characters(model_hparams):
  """English to parse tree translation benchmark."""
  del model_hparams  # Unused.
  p = default_problem_hparams()
  p.input_modality = {"inputs": (registry.Modalities.SYMBOL, 256)}
  p.target_modality = (registry.Modalities.SYMBOL, 256)
  p.vocabulary = {
      "inputs": text_encoder.ByteTextEncoder(),
      "targets": text_encoder.ByteTextEncoder(),
  }
  p.loss_multiplier = 2.0
  p.input_space_id = 2
  p.target_space_id = 14
  return p


def wmt_parsing_tokens(model_hparams, wrong_vocab_size):
  """English to parse tree translation benchmark.

  Args:
    model_hparams: a tf.contrib.training.HParams
    wrong_vocab_size: a number used in the filename indicating the approximate
      vocabulary size.  This is not to be confused with the actual vocabulary
      size.
  Returns:
    a tf.contrib.training.HParams
  """
  p = default_problem_hparams()
  # This vocab file must be present within the data directory.
  vocab_filename = os.path.join(model_hparams.data_dir,
                                "vocab.endefr.%d" % wrong_vocab_size)
  subtokenizer = text_encoder.SubwordTextEncoder(vocab_filename)
  p.input_modality = {
      "inputs": (registry.Modalities.SYMBOL, subtokenizer.vocab_size)
  }
  p.target_modality = (registry.Modalities.SYMBOL, subtokenizer.vocab_size)
  p.vocabulary = {
      "inputs": subtokenizer,
      "targets": subtokenizer,
  }
  p.input_space_id = 3
  p.target_space_id = 15
  return p


def wsj_parsing_tokens(model_hparams, prefix, wrong_source_vocab_size,
                       wrong_target_vocab_size):
  """English to parse tree translation benchmark.

  Args:
    model_hparams: a tf.contrib.training.HParams
    prefix: name to use as prefix for vocabulary files.
    wrong_source_vocab_size: a number used in the filename indicating the
      approximate vocabulary size.  This is not to be confused with the actual
      vocabulary size.
    wrong_target_vocab_size: a number used in the filename indicating the
      approximate target vocabulary size. This is not to be confused with the
      actual target vocabulary size.
  Returns:
    a tf.contrib.training.HParams
  """
  p = default_problem_hparams()
  # This vocab file must be present within the data directory.
  source_vocab_filename = os.path.join(
      model_hparams.data_dir,
      prefix + "_source.vocab.%d" % wrong_source_vocab_size)
  target_vocab_filename = os.path.join(
      model_hparams.data_dir,
      prefix + "_target.vocab.%d" % wrong_target_vocab_size)
  source_subtokenizer = text_encoder.SubwordTextEncoder(source_vocab_filename)
  target_subtokenizer = text_encoder.SubwordTextEncoder(target_vocab_filename)
  p.input_modality = {
      "inputs": (registry.Modalities.SYMBOL, source_subtokenizer.vocab_size)
  }
  p.target_modality = (registry.Modalities.SYMBOL,
                       target_subtokenizer.vocab_size)
  p.vocabulary = {
      "inputs": source_subtokenizer,
      "targets": target_subtokenizer,
  }
  p.input_space_id = 3
  p.target_space_id = 15
  return p


def img2img_imagenet(unused_model_hparams):
  """Image 2 Image for imagenet dataset."""
  p = default_problem_hparams()
  p.input_modality = {"inputs": ("image:identity", None)}
  p.target_modality = ("image:identity", None)
  p.batch_size_multiplier = 256
  p.max_expected_batch_size_per_shard = 4
  p.input_space_id = 1
  p.target_space_id = 1
  return p


# Dictionary of named hyperparameter settings for various problems.
# This is only accessed through the problem_hparams function below.
PROBLEM_HPARAMS_MAP = {
    "audio_timit_characters_tune":
        audio_timit_characters,
    "audio_timit_characters_test":
        audio_timit_characters,
    "audio_timit_tokens_8k_tune":
        lambda p: audio_timit_tokens(p, 2**13),
    "audio_timit_tokens_8k_test":
        lambda p: audio_timit_tokens(p, 2**13),
    "parsing_english_ptb8k":
        lambda p: wmt_parsing_tokens(p, 2**13),
    "parsing_english_ptb16k":
        lambda p: wsj_parsing_tokens(  # pylint: disable=g-long-lambda
            p, "wsj", 2**14, 2**9),
    "img2img_imagenet":
        img2img_imagenet,
}
