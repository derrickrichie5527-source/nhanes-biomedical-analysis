"""Tests use the actual public NHANES records, not a synthetic dataset."""
from pathlib import Path
import sys
import sqlite3
import unittest
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from pipeline import ROOT, LABS, get_sources, prepare, validate_keys

class DataIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw_bio,cls.raw_demo=get_sources()
        cls.bio,cls.demo,cls.joined,cls.adults,cls.long,cls.log,cls.bounds=prepare(cls.raw_bio,cls.raw_demo)

    def test_real_source_counts_and_join(self):
        self.assertEqual((len(self.raw_bio),len(self.raw_demo)),(6401,9254))
        self.assertEqual(len(self.joined),6401)
        self.assertEqual(len(self.adults),5265)
        self.assertTrue(self.adults.SEQN.is_unique)

    def test_no_analyte_imputation_or_removal(self):
        original=self.raw_bio.set_index('SEQN').loc[self.adults.SEQN,list(LABS)]
        result=self.adults.set_index('SEQN')[list(LABS)]
        pd.testing.assert_frame_equal(original.reset_index(drop=True),result.reset_index(drop=True),check_dtype=False)

    def test_null_preserving_reshape_and_roundtrip(self):
        self.assertEqual(len(self.long),31590)
        self.assertFalse(self.long.duplicated(['SEQN','Biomarker']).any())
        self.assertEqual(int(self.long.IsMissing.sum()),2111)
        wide=self.long.pivot(index='SEQN',columns='SourceVariable',values='Value').sort_index()[list(LABS)]
        original=self.adults.set_index('SEQN').sort_index()[list(LABS)]
        wide.columns.name=None
        pd.testing.assert_frame_equal(wide,original,check_dtype=False)

    def test_detection_codes_and_flags(self):
        for name in ['LBDSATLC','LBDSGTLC']:
            self.assertLessEqual(set(self.adults[name].dropna()),{0,1})
        self.assertTrue(self.long.loc[self.long.IsMissing.eq(1),'IQRReviewFlag'].isna().all())
        self.assertEqual(int(self.long.IQRReviewFlag.sum()),1457)

    def test_duplicate_real_record_rejected(self):
        # Deliberately duplicate an existing record only to test the key guard.
        duplicate=pd.concat([self.raw_bio,self.raw_bio.iloc[:1]],ignore_index=True)
        with self.assertRaises(ValueError): validate_keys(duplicate,'duplicate-test')

    def test_database_constraints_and_cross_tool_counts(self):
        with sqlite3.connect(ROOT/'data/processed/nhanes.sqlite') as con:
            self.assertEqual(con.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(con.execute('PRAGMA foreign_key_check').fetchall(),[])
            self.assertEqual(con.execute('SELECT COUNT(*) FROM v_adults').fetchone()[0],5265)
            self.assertEqual(con.execute('SELECT COUNT(*) FROM v_long').fetchone()[0],31590)
            self.assertEqual(con.execute('SELECT COUNT(*) FROM v_grouped_stats').fetchone()[0],48)
            self.assertEqual(con.execute('SELECT SUM(IsMissing) FROM v_long').fetchone()[0],2111)

if __name__=='__main__': unittest.main()
