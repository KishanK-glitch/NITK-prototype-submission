# External Libraries
import unittest

# Internal Project Imports
from app.core.config import load_rules


class TestGovernmentSchemeRules(unittest.TestCase):

    def test_pm_kisan_rules_load(self):
        rules = load_rules("pm_kisan")

        self.assertEqual(
            rules["scheme"]["short_name"],
            "PM-KISAN"
        )

    def test_pm_fasal_bima_rules_load(self):
        rules = load_rules("pm_fasal_bima")

        self.assertEqual(
            rules["scheme"]["short_name"],
            "PMFBY"
        )

    def test_pm_kisan_land_limit(self):
        rules = load_rules("pm_kisan")

        self.assertEqual(
            rules["eligibility"]["maximum_land_area_hectares"],
            2.0
        )

    def test_pm_kisan_institutional_landholder_exclusion(self):
        rules = load_rules("pm_kisan")

        self.assertTrue(
            rules["exclusions"]["institutional_landholder"]
        )

    def test_pm_kisan_income_tax_exclusion(self):
        rules = load_rules("pm_kisan")

        self.assertTrue(
            rules["exclusions"]["income_tax_payer"][
                "excluded_if_paid_tax_in_last_assessment_year"
            ]
        )

    def test_pm_kisan_pension_threshold(self):
        rules = load_rules("pm_kisan")

        self.assertEqual(
            rules["exclusions"]["retired_pensioner"][
                "excluded_if_monthly_pension_inr_gte"
            ],
            10000
        )

    def test_pm_kisan_ekyc(self):
        rules = load_rules("pm_kisan")

        self.assertTrue(
            rules["verification"]["ekyc_mandatory"]
        )

    def test_pm_fasal_bima_insurable_interest(self):
        rules = load_rules("pm_fasal_bima")

        self.assertTrue(
            rules["eligibility"]["farmer_must_have_insurable_interest"]
        )

    def test_pm_fasal_bima_notified_crop(self):
        rules = load_rules("pm_fasal_bima")

        self.assertTrue(
            rules["eligibility"]["notified_crop_required"]
        )

    def test_pm_fasal_bima_notified_area(self):
        rules = load_rules("pm_fasal_bima")

        self.assertTrue(
            rules["eligibility"]["notified_area_required"]
        )

    def test_pm_fasal_bima_notified_season(self):
        rules = load_rules("pm_fasal_bima")

        self.assertTrue(
            rules["eligibility"]["notified_season_required"]
        )

    def test_pm_fasal_bima_premium_kharif(self):
        rules = load_rules("pm_fasal_bima")

        self.assertEqual(
            rules["crop_categories"]["kharif_food_and_oilseed"][
                "maximum_farmer_premium_percent"
            ],
            2.0
        )

    def test_pm_fasal_bima_premium_rabi(self):
        rules = load_rules("pm_fasal_bima")

        self.assertEqual(
            rules["crop_categories"]["rabi_food_and_oilseed"][
                "maximum_farmer_premium_percent"
            ],
            1.5
        )

    def test_pm_fasal_bima_premium_commercial(self):
        rules = load_rules("pm_fasal_bima")

        self.assertEqual(
            rules["crop_categories"]["annual_commercial_or_horticultural"][
                "maximum_farmer_premium_percent"
            ],
            5.0
        )
    def test_pmjay_rules_load(self):
            rules = load_rules("pmjay")
            self.assertEqual(
                rules["scheme"]["short_name"],
                "PM-JAY"
       )
    
    def test_pmjay_health_cover(self):
        rules = load_rules("pmjay")
        
        self.assertEqual(
            rules["benefits"]["annual_health_cover_inr"],
            500000
        )

    
    def test_pmjay_senior_citizen_age(self):
        rules = load_rules("pmjay")
    
        self.assertEqual(
            rules["eligibility"]["senior_citizen_70_plus"]["minimum_age_years"],
                70
        )
    
    def test_pmjay_senior_citizen_income_independent(self):
        rules = load_rules("pmjay")
    
        self.assertTrue(
            rules["eligibility"]["senior_citizen_70_plus"]["income_independent"]
        )
    
    def test_pmjay_aadhaar_ekyc(self):
        rules = load_rules("pmjay")
    
        self.assertTrue(rules["verification"]["aadhaar_based_ekyc_for_70_plus"]
        )
    
    def test_pmjay_beneficiary_database_verification(self):
        rules = load_rules("pmjay")
    
        self.assertTrue(
        rules["verification"]["beneficiary_database_verification"]
            )
    def test_pmay_g_rules_load(self):
        rules = load_rules("pmay_g")

        self.assertEqual(
            rules["scheme"]["short_name"],
            "PMAY-G"
        )

    def test_pmay_g_rural_household_required(self):
        rules = load_rules("pmay_g")

        self.assertTrue(
            rules["eligibility"]["rural_household_required"]
        )

    def test_pmay_g_maximum_rooms(self):
        rules = load_rules("pmay_g")

        self.assertEqual(
            rules["eligibility"]["maximum_rooms"],
            2
        )

    def test_pmay_g_income_exclusion(self):
        rules = load_rules("pmay_g")

        self.assertEqual(
            rules["exclusions"]["monthly_family_income"][
                "excluded_if_any_member_income_inr_gt"
            ],
            15000
        )

    def test_pmay_g_kcc_exclusion(self):
        rules = load_rules("pmay_g")

        self.assertEqual(
            rules["exclusions"]["kisan_credit_card"][
                "excluded_if_credit_limit_inr_gte"
            ],
            50000
        )

    def test_pmay_g_house_assistance(self):
        rules = load_rules("pmay_g")

        self.assertEqual(
            rules["benefits"]["unit_assistance_plain_area_inr"],
            120000
        )
    def test_pm_ujjwala_rules_load(self):
        rules = load_rules("pm_ujjwala")

        self.assertEqual(
            rules["scheme"]["short_name"],
            "PMUY"
        )

    def test_pm_ujjwala_minimum_age(self):
        rules = load_rules("pm_ujjwala")

        self.assertEqual(
            rules["eligibility"]["minimum_age_years"],
            18
        )

    def test_pm_ujjwala_woman_applicant(self):
        rules = load_rules("pm_ujjwala")

        self.assertEqual(
            rules["eligibility"]["applicant_gender"],
            "female"
        )

    def test_pm_ujjwala_poor_household(self):
        rules = load_rules("pm_ujjwala")

        self.assertTrue(
            rules["eligibility"]["poor_household_required"]
        )

    def test_pm_ujjwala_no_existing_lpg(self):
        rules = load_rules("pm_ujjwala")

        self.assertFalse(
            rules["eligibility"]["existing_lpg_connection_in_household"]
        )

    def test_pm_ujjwala_lpg_verification(self):
        rules = load_rules("pm_ujjwala")

        self.assertTrue(
            rules["verification"]["existing_lpg_connection_check"]
        )
    def test_pm_svanidhi_rules_load(self):
        rules = load_rules("pm_svanidhi")

        self.assertEqual(
            rules["scheme"]["short_name"],
            "PM SVANidhi"
        )

    def test_pm_svanidhi_street_vendor_required(self):
        rules = load_rules("pm_svanidhi")

        self.assertTrue(
            rules["eligibility"]["street_vendor_required"]
        )

    def test_pm_svanidhi_first_tranche(self):
        rules = load_rules("pm_svanidhi")

        self.assertEqual(
            rules["loan"]["first_tranche"]["maximum_amount_inr"],
            15000
        )

    def test_pm_svanidhi_second_tranche(self):
        rules = load_rules("pm_svanidhi")

        self.assertEqual(
            rules["loan"]["second_tranche"]["maximum_amount_inr"],
            25000
        )

    def test_pm_svanidhi_third_tranche(self):
        rules = load_rules("pm_svanidhi")

        self.assertEqual(
            rules["loan"]["third_tranche"]["maximum_amount_inr"],
            50000
        )

    def test_pm_svanidhi_vendor_verification(self):
        rules = load_rules("pm_svanidhi")

        self.assertTrue(
            rules["verification"]["vendor_identity_verification"]
        )
    def test_pm_vishwakarma_rules_load(self):
        rules = load_rules("pm_vishwakarma")

        self.assertEqual(
            rules["scheme"]["short_name"],
            "PM Vishwakarma"
        )

    def test_pm_vishwakarma_minimum_age(self):
        rules = load_rules("pm_vishwakarma")

        self.assertEqual(
            rules["eligibility"]["minimum_age_years"],
            18
        )

    def test_pm_vishwakarma_notified_trade_required(self):
        rules = load_rules("pm_vishwakarma")

        self.assertTrue(
            rules["eligibility"]["engaged_in_notified_trade"]
        )

    def test_pm_vishwakarma_one_beneficiary_per_family(self):
        rules = load_rules("pm_vishwakarma")

        self.assertEqual(
            rules["family_rules"]["maximum_beneficiary_members_per_family"],
            1
        )

    def test_pm_vishwakarma_first_loan(self):
        rules = load_rules("pm_vishwakarma")

        self.assertEqual(
            rules["loan"]["first_tranche"]["maximum_amount_inr"],
            100000
        )

    def test_pm_vishwakarma_toolkit_incentive(self):
        rules = load_rules("pm_vishwakarma")

        self.assertEqual(
            rules["benefits"]["toolkit_incentive_maximum_inr"],
            15000
        )
    def test_pm_kmy_rules_load(self):
        rules = load_rules("pm_kisan_maandhan")

        self.assertEqual(
            rules["scheme"]["short_name"],
            "PM-KMY"
        )

    def test_pm_kmy_minimum_entry_age(self):
        rules = load_rules("pm_kisan_maandhan")

        self.assertEqual(
            rules["eligibility"]["minimum_entry_age_years"],
            18
        )

    def test_pm_kmy_maximum_entry_age(self):
        rules = load_rules("pm_kisan_maandhan")

        self.assertEqual(
            rules["eligibility"]["maximum_entry_age_years"],
            40
        )

    def test_pm_kmy_land_limit(self):
        rules = load_rules("pm_kisan_maandhan")

        self.assertEqual(
            rules["eligibility"]["maximum_land_area_hectares"],
            2.0
        )

    def test_pm_kmy_monthly_pension(self):
        rules = load_rules("pm_kisan_maandhan")

        self.assertEqual(
            rules["benefits"]["minimum_monthly_pension_inr"],
            3000
        )

    def test_pm_kmy_government_matching_contribution(self):
        rules = load_rules("pm_kisan_maandhan")

        self.assertTrue(
            rules["contribution"]["government_matching_contribution"]
        )
    def test_pmjdy_rules_load(self):
        rules = load_rules("pmjdy")

        self.assertEqual(
            rules["scheme"]["short_name"],
            "PMJDY"
        )

    def test_pmjdy_unbanked_person_required(self):
        rules = load_rules("pmjdy")

        self.assertTrue(
            rules["eligibility"]["unbanked_person_required"]
        )

    def test_pmjdy_no_minimum_balance(self):
        rules = load_rules("pmjdy")

        self.assertFalse(
            rules["account"]["minimum_balance_required"]
        )

    def test_pmjdy_rupay_card(self):
        rules = load_rules("pmjdy")

        self.assertTrue(
            rules["account"]["ruPay_debit_card"]
        )

    def test_pmjdy_overdraft_limit(self):
        rules = load_rules("pmjdy")

        self.assertEqual(
            rules["overdraft"]["maximum_amount_inr"],
            10000
        )

    def test_pmjdy_kyc_verification(self):
        rules = load_rules("pmjdy")

        self.assertTrue(
            rules["verification"]["kyc_verification"]
        )
    def test_apy_rules_load(self):
        rules = load_rules("atal_pension")

        self.assertEqual(
            rules["scheme"]["short_name"],
            "APY"
        )

    def test_apy_minimum_entry_age(self):
        rules = load_rules("atal_pension")

        self.assertEqual(
            rules["eligibility"]["minimum_entry_age_years"],
            18
        )

    def test_apy_maximum_entry_age(self):
        rules = load_rules("atal_pension")

        self.assertEqual(
            rules["eligibility"]["maximum_entry_age_years"],
            40
        )

    def test_apy_pension_start_age(self):
        rules = load_rules("atal_pension")

        self.assertEqual(
            rules["pension"]["pension_start_age_years"],
            60
        )

    def test_apy_maximum_pension(self):
        rules = load_rules("atal_pension")

        self.assertEqual(
            rules["pension"]["maximum_monthly_pension_inr"],
            5000
        )

    def test_apy_income_taxpayer_exclusion(self):
        rules = load_rules("atal_pension")

        self.assertTrue(
            rules["exclusions"]["income_taxpayer_new_subscriber"]
        )
    def test_nsap_rules_load(self):
        rules = load_rules("nsap")

        self.assertEqual(
            rules["scheme"]["short_name"],
            "NSAP"
        )

    def test_nsap_ignoaps_minimum_age(self):
        rules = load_rules("nsap")

        self.assertEqual(
            rules["components"]["ignoaps"]["minimum_age_years"],
            60
        )

    def test_nsap_ignwps_minimum_age(self):
        rules = load_rules("nsap")

        self.assertEqual(
            rules["components"]["ignwps"]["minimum_age_years"],
            40
        )

    def test_nsap_igndps_disability_requirement(self):
        rules = load_rules("nsap")

        self.assertEqual(
            rules["components"]["igndps"]["minimum_disability_percent"],
            80
        )

    def test_nsap_nfbs_assistance(self):
        rules = load_rules("nsap")

        self.assertEqual(
            rules["components"]["nfbs"]["one_time_assistance_inr"],
            20000
        )

    def test_nsap_annapurna_food_grain(self):
        rules = load_rules("nsap")

        self.assertEqual(
            rules["components"]["annapurna"]["food_grain_per_month_kg"],
            10
        )  
if __name__ == "__main__":
    unittest.main()