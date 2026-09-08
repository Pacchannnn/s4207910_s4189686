"""Arithmetic regressions. Synthetic rows are test fixtures, never website data."""
import sqlite3
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class QueryTests(unittest.TestCase):
    def setUp(self):
        from immunisation_app.queries import Queries
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        source = sqlite3.connect((ROOT / "database/immunisation.db").as_uri()+"?mode=ro", uri=True)
        try:
            for row in source.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
                self.db.execute(row[0])
        finally:
            source.close()
        self.db.executemany("INSERT INTO YearDate VALUES (?)", [(2000,), (2024,)])
        self.db.execute("INSERT INTO Region VALUES ('REG','Test region')")
        self.db.execute("INSERT INTO Economy VALUES (1,'Test economy')")
        self.db.executemany("INSERT INTO Country VALUES (?,?,'REG',?)",
                            [('AAA','Alpha',1),('BBB','Beta',1),('CCC','Gamma',''),('DDD','Delta',1)])
        self.db.execute("INSERT INTO Antigen VALUES ('VAC','Test antigen')")
        self.db.execute("INSERT INTO Infection_Type VALUES ('DIS','Test infection')")
        self.db.executemany("INSERT INTO CountryPopulation VALUES (?,?,?)",
                            [('AAA',2000,1000),('AAA',2024,2000),
                             ('BBB',2000,1000),('BBB',2024,1000),
                             ('CCC',2000,1000),('CCC',2024,1000),
                             ('DDD',2000,1000),('DDD',2024,0)])
        self.db.executemany("INSERT INTO Vaccination VALUES ('DIS','VAC',?,?,?,?,?)",
                            [('AAA',2000,100,100,100),('AAA',2024,300,300,100),
                             ('BBB',2000,100,100,100),('BBB',2024,200,200,100),
                             ('CCC',2000,100,'',''),('CCC',2024,200,100,150),
                             ('DDD',2000,100,100,100),('DDD',2024,200,100,50)])
        self.db.executemany("INSERT INTO InfectionData VALUES ('DIS',?,2024,?)",
                            [('AAA',20),('BBB',30),('CCC',0),('DDD',900)])
        self.db.executescript((ROOT / "database/extensions.sql").read_text(encoding="utf-8"))
        self.q = Queries(self.db)

    def tearDown(self):
        self.db.close()

    def test_global_benchmark_is_population_weighted_and_excludes_zero_denominator(self):
        result = self.q.benchmark(2024, 'DIS', 'rate', 'desc')
        self.assertAlmostEqual(result['global']['rate'], 1250.0)
        self.assertEqual(result['global']['cases'], 50)
        self.assertEqual(result['global']['population'], 4000)
        self.assertEqual(result['global']['countries'], 3)
        self.assertEqual([r['country'] for r in result['rows']], ['Beta'])
        self.assertAlmostEqual(result['rows'][0]['rate'], 3000)
        self.assertEqual(result['excluded'], 1)

    def test_population_change_affects_improvement_and_top_n_precedes_display_sort(self):
        result = self.q.improvements(2000, 2024, 'VAC', 1, 'country', 'asc')
        self.assertEqual([r['country'] for r in result['rows']], ['Beta'])
        self.assertAlmostEqual(result['rows'][0]['increase'], 10)
        result = self.q.improvements(2000, 2024, 'VAC', 4, 'country', 'asc')
        self.assertEqual([r['country'] for r in result['rows']], ['Alpha', 'Beta'])
        self.assertAlmostEqual(result['rows'][0]['start_rate'], 10)
        self.assertAlmostEqual(result['rows'][0]['end_rate'], 15)
        self.assertAlmostEqual(result['rows'][0]['increase'], 5)

    def test_missing_endpoint_and_zero_population_never_produce_improvement(self):
        result = self.q.improvements(2000, 2024, 'VAC', 4, 'increase', 'desc')
        self.assertEqual(result['eligible'], 2)
        self.assertEqual(result['excluded'], 2)

    def test_coverage_above_100_is_flagged_and_regional_summary_is_unbiased_by_minimum(self):
        result = self.q.vaccinations(2024, 'VAC', '', '', 90, 90, 'country', 'asc')
        self.assertEqual([r['country'] for r in result['rows']], ['Alpha', 'Beta', 'Gamma'])
        self.assertEqual(result['rows'][2]['anomaly'], 1)
        region = result['regions'][0]
        self.assertEqual(region['available'], 4)
        self.assertEqual(region['meeting'], 3)
        self.assertAlmostEqual(region['mean_coverage'], 100)
        self.assertEqual(region['missing'], 0)

    def test_economic_summary_uses_cases_and_population_not_mean_of_rates(self):
        result = self.q.infections(2024,'DIS','1','',{},'country','asc')
        self.assertEqual([r['country'] for r in result['rows']], ['Alpha','Beta','Delta'])
        summary = result['summary'][0]
        self.assertEqual(summary['cases'], 950)
        self.assertEqual(summary['matched_cases'], 50)
        self.assertEqual(summary['population'], 3000)
        self.assertAlmostEqual(summary['rate'], 50000/30)
        self.assertEqual(result['unknown_economy'], 1)

    def test_detail_numeric_filter_does_not_change_all_economy_summary(self):
        result = self.q.infections(2024,'DIS','1','',{'min_rate':2000},'rate','desc')
        self.assertEqual([r['country'] for r in result['rows']], ['Beta'])
        self.assertEqual(result['summary'][0]['cases'], 950)

    def test_zero_cases_are_kept_and_missing_cases_are_excluded_from_benchmark(self):
        self.db.execute("UPDATE InfectionData SET cases='' WHERE country='BBB'")
        result = self.q.benchmark(2024, 'DIS', 'rate', 'desc')
        self.assertEqual(result['global']['countries'], 2)
        self.assertEqual(result['global']['population'], 3000)
        self.assertEqual(result['global']['cases'], 20)

    def test_no_data_returns_empty_and_no_global_rate(self):
        result = self.q.benchmark(2000,'DIS','rate','desc')
        self.assertIsNone(result['global']['rate'])
        self.assertEqual(result['rows'], [])
        result = self.q.vaccinations(2000,'VAC','AAA','OTHER',0,90,'country','asc')
        self.assertEqual(result['rows'], [])

    def test_same_or_falling_rate_is_not_a_positive_improvement(self):
        self.db.execute("UPDATE Vaccination SET doses=50 WHERE year=2024")
        self.assertEqual(self.q.improvements(2000,2024,'VAC',10,'increase','desc')['rows'], [])

    def test_sql_sort_whitelist_rejects_injection_even_when_called_directly(self):
        with self.assertRaises(ValueError):
            self.q.benchmark(2024,'DIS','rate; DROP TABLE Country','desc')
        with self.assertRaises(ValueError):
            self.q.benchmark(2024,'DIS','rate','desc; DROP TABLE Country')

    def test_facts_reflect_reference_tables_not_hardcoded_totals(self):
        facts = self.q.facts()
        self.assertEqual((facts['first_year'], facts['last_year'], facts['countries'], facts['infections'], facts['antigens']),
                         (2000, 2024, 4, 1, 1))
        self.db.execute("INSERT INTO Infection_Type VALUES ('NEW','New test infection')")
        self.assertEqual(self.q.facts()['infections'], 2)
        self.db.execute("INSERT INTO InfectionData VALUES ('NEW','AAA',2024,2)")
        self.assertEqual(self.q.facts()['infections'], 2)

    def test_mission_reads_updated_persona_and_team_records(self):
        self.db.execute("INSERT INTO Persona(persona_id,name,profile,goal,difficulty) VALUES (99,'Test name','Test profile','Test goal','Test difficulty')")
        self.db.execute("INSERT INTO TeamMember VALUES ('test-id','Test member')")
        self.assertEqual(self.q.mission()['personas'][0]['name'], 'Test name')
        self.assertEqual(self.q.mission()['team'][0]['name'], 'Test member')
        self.db.execute("UPDATE Persona SET name='Updated test name' WHERE persona_id=99")
        self.assertEqual(self.q.mission()['personas'][0]['name'], 'Updated test name')

    def test_coverage_fallback_is_labelled_and_missing_is_not_zero(self):
        self.db.execute("UPDATE Vaccination SET coverage='' WHERE country='AAA' AND year=2024")
        self.db.execute("UPDATE Vaccination SET doses=0, coverage='' WHERE country='BBB' AND year=2024")
        result = self.q.vaccinations(2024, 'VAC', '', '', 0, 90, 'country', 'asc')
        rows = {r['country']: r for r in result['rows']}
        self.assertEqual(rows['Alpha']['coverage'], 100)
        self.assertEqual(rows['Alpha']['coverage_source'], 'Calculated')
        self.assertEqual(rows['Beta']['coverage'], 0)
        self.assertEqual(rows['Beta']['coverage_source'], 'Calculated')
        missing = self.q.vaccinations(2000, 'VAC', 'CCC', '', 0, 90, 'country', 'asc')
        self.assertEqual(missing['rows'], [])

    def test_multiple_dose_rows_sum_before_population_join(self):
        self.db.execute("INSERT INTO Infection_Type VALUES ('ALT','Alternative')")
        self.db.execute("INSERT INTO Vaccination VALUES ('ALT','VAC','AAA',2024,100,100,100)")
        result = self.q.improvements(2000, 2024, 'VAC', 4, 'country', 'asc')
        alpha = next(r for r in result['rows'] if r['country'] == 'Alpha')
        self.assertEqual(alpha['end_doses'], 400)
        self.assertEqual(alpha['end_rate'], 20)
        self.assertEqual(alpha['increase'], 10)

    def test_real_zero_endpoint_is_kept(self):
        self.db.execute("UPDATE Vaccination SET doses=0 WHERE country='AAA' AND year=2000")
        result = self.q.improvements(2000, 2024, 'VAC', 4, 'country', 'asc')
        alpha = next(r for r in result['rows'] if r['country'] == 'Alpha')
        self.assertEqual(alpha['start_rate'], 0)
        self.assertEqual(alpha['increase'], 15)

if __name__ == '__main__':
    unittest.main()
