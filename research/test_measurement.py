"""Checks that protect against plausible but invalid energy results."""
import unittest
import numpy as np
from experiment import clip_series,counter_window

class MeasurementChecks(unittest.TestCase):
 def test_interpolated_boundaries(self):
  p=np.array([[0,0],[5,50],[10,100]],dtype=float)
  out=clip_series(p,2,8)
  self.assertAlmostEqual(out[-1,1]-out[0,1],60)
 def test_loaded_guard_avoids_cutoff_step_bias(self):
  # At 40 W, true energy at t=8 is 320 J. A stop at 8 followed by
  # 5 W idle gives a t=10 sample of 330 J and biases interpolation.
  stopped=np.array([[0,0],[5,200],[10,330]],float)
  guarded=np.array([[0,0],[5,200],[10,400]],float)
  self.assertLess(clip_series(stopped,1,8)[-1,1],320)
  self.assertAlmostEqual(clip_series(guarded,1,8)[-1,1],320)
 def test_missing_metric_is_error(self):
  with self.assertRaises(AssertionError):counter_window([],1,9)
 def test_counter_restart_invalidates_window(self):
  data=[{'values':[[0,'100'],[5,'10'],[10,'20']]}]
  with self.assertRaises(AssertionError):counter_window(data,1,9)
 def test_unbracketed_interval_is_error(self):
  with self.assertRaises(AssertionError):clip_series(np.array([[5,50],[10,100]],float),2,8)
 def test_missing_scrape_gap_is_error(self):
  with self.assertRaises(AssertionError):clip_series(np.array([[0,0],[20,200]],float),1,19)
 def test_sum_two_independent_counters(self):
  data=[{'values':[[0,'1'],[5,'11'],[10,'21']]},{'values':[[0,'2'],[5,'22'],[10,'42']]}]
  out=counter_window(data,2,8)
  self.assertAlmostEqual(out[-1,1]-out[0,1],36)
if __name__=='__main__':unittest.main()
