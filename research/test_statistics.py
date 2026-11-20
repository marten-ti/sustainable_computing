import unittest
import numpy as np
from analyze import permutation_p,permutations,simulate

class StatisticalChecks(unittest.TestCase):
 def test_small_n_has_no_five_percent_resolution(self):
  self.assertAlmostEqual(permutation_p([1,2],[10,11]),1/6)
 def test_n3_minimum_p(self):
  self.assertAlmostEqual(permutation_p([1,2,3],[10,11,12]),1/20)
 def test_wrong_direction(self):
  self.assertEqual(permutation_p([10,11,12],[1,2,3]),1)
 def test_ties_are_conservative(self):
  self.assertEqual(permutation_p([1,1,1],[1,1,1]),1)
 def test_balanced_permutation_matrix(self):
  m=permutations(4)
  self.assertEqual(m.shape,(70,8));self.assertTrue(np.allclose(m.sum(axis=1),0))
 def test_aa_conditional_calibration(self):
  rate,count=simulate(np.arange(1.,9.),4,0)
  self.assertEqual(count,70);self.assertLessEqual(rate,.05)
if __name__=='__main__':unittest.main()
