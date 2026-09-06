# Phase J2.1-R1 Test Execution Evidence & Report

```text
================================================================================
                    PHASE J2.1-R1 OFFLINE TEST EXECUTION REPORT
================================================================================
Command Invoked:    python3 -m unittest discover -s tools/rmg-eze4/tests -v
Working Directory:  /Users/markpi/tab-s9-fe-linux
Interpreter:        /opt/homebrew/bin/python3 (Python 3.14.7)
Git Commit / Ref:   ab7b76e (branch main)
Timestamp:          2026-09-06T19:34:04+02:00
Exit Code:          0 (SUCCESS)
================================================================================

Test File Breakdown:
--------------------------------------------------------------------------------
1. test_phase_i_analysis.py (Phase I Regression Suite)
   - test_all_12_groups_three_way                                            PASS
   - test_all_19_parameters_positive_and_negative                           PASS
   - test_attribution_rules                                                  PASS
   - test_cross_boot_and_condition_requirements                              PASS
   - test_edge_case_fixture                                                  PASS
   - test_evidence_totals_and_enforcement                                    PASS
   - test_five_must_validate_six_scenarios                                   PASS
   - test_p0_uncertainty_is_preserved                                        PASS
   - test_synthetic_campaign_shape                                           PASS

2. test_phase_j0_selection.py (Phase J0 Selection Suite)
   - test_attribution_failure_is_inconclusive                                PASS
   - test_below_minimum_is_inconclusive                                      PASS
   - test_compatible                                                         PASS
   - test_cross_condition_requirement                                        PASS
   - test_incompatible                                                       PASS
   - test_missing_provenance_is_invalid                                      PASS

3. test_phase_j2_1_r1_consistency.py (Cross-Artifact Consistency Checker — 1 test)
   - test_cross_artifact_consistency                                         PASS

4. test_phase_j2_1_r1_replay.py (End-to-End RAW Replay Pipeline Suite — 28 tests)
   - test_scn_01_clean_compatible_campaign                                   PASS
   - test_scn_02_single_attributable_timeout_is_inconclusive                 PASS
   - test_scn_03_incompatibility_threshold_3_same_condition_2_boots           PASS
   - test_scn_04_isolated_boot_timeouts_are_inconclusive                     PASS
   - test_scn_05_cross_condition_timeouts_are_inconclusive                   PASS
   - test_scn_06_boundary_2195_exact                                         PASS
   - test_scn_07_boundary_2197_mid                                           PASS
   - test_scn_08_invalid_cap_exceeded_single_boot                             PASS
   - test_scn_09_invalid_cap_exceeded_total                                   PASS
   - test_scn_10_child_exit_nonzero_with_intact_telemetry                    PASS
   - test_scn_11_child_signal_crash_with_intact_telemetry                    PASS
   - test_scn_12_p0_duration_does_not_reset_candidate_epoch                  PASS
   - test_scn_13_watchdog_boundary_2200_exact                                PASS
   - test_scn_14_confounder_c1_present_is_invalid                            PASS
   - test_scn_15_confounder_c1_unknown_is_inconclusive                       PASS
   - test_scn_16_confounder_c2_freeze_is_invalid                            PASS
   - test_scn_17_confounder_c2_gap_is_inconclusive                           PASS
   - test_scn_18_confounder_c3_thermal_is_invalid                            PASS
   - test_scn_19_confounder_c3_gap_is_inconclusive                           PASS
   - test_scn_20_clock_corruption_step_backward                             PASS
   - test_scn_21_clock_correlation_desync                                    PASS
   - test_scn_22_boot_mutation_mid_trial                                     PASS
   - test_scn_23_unknown_event_grammar_version                               PASS
   - test_scn_24_wrong_stock_image_hash                                      PASS
   - test_scn_25_unbound_run_package_is_template_valid                       PASS
   - test_scn_26_wrong_build_fingerprint_rejected                            PASS
   - test_scn_27_wrong_kernel_identity_rejected                              PASS
   - test_scn_28_wrong_device_codename_rejected                              PASS

5. test_phase_j2_1_r1_schema.py (Schema v2.2.1 & Event Grammar v2.1.1 Suite — 20 tests)
   - test_positive_canonical_record                                          PASS
   - test_neg_01_empty_artifact_identity                                     PASS
   - test_neg_02_forbidden_field                                             PASS
   - test_neg_03_invalid_enum_validity                                       PASS
   - test_neg_04_bad_sha256_format                                           PASS
   - test_neg_05_duration_mismatch                                           PASS
   - test_neg_06_headroom_mismatch                                           PASS
   - test_neg_07_clock_correlation_desync_1_1s                               PASS
   - test_neg_08_boot_mutation_mid_trial                                     PASS
   - test_neg_09_pid_mismatch_in_events                                      PASS
   - test_neg_10_illegal_reap_before_spawn                                   PASS
   - test_neg_11_confounder_c2_freeze_with_valid_vote                        PASS
   - test_neg_12_confounder_unknown_with_valid_vote                          PASS
   - test_neg_13_compatible_vote_exceeds_2195_headroom                       PASS
   - test_neg_identity_5_15_189_wrong_kernel_build_identity                  PASS
   - test_neg_identity_correct_incremental_wrong_fingerprint                 PASS
   - test_neg_identity_correct_model_wrong_device_codename                   PASS
   - test_neg_identity_fingerprint_csc_segment_changed                       PASS
   - test_neg_identity_wrong_full_build_fingerprint                         PASS
   - test_neg_identity_wrong_stock_image_sha256                              PASS

6. test_phase_j2_design.py (Canonical Phase J2 Design & Boundary Suite — 4 tests)
   - test_canonical_campaign_scenarios (12 canonical campaign scenarios)     PASS
   - test_semantic_boundary_single_timeout_is_inconclusive                  PASS
   - test_adversarial_neighboring_boundaries                                PASS
   - test_no_engine_import_in_j2 (AST regression guard)                     PASS

--------------------------------------------------------------------------------
TOTAL SUITE TESTS:  68
PASSED:             68
FAILED:              0
SKIPPED:             0
PASS RATE:          100.0%
================================================================================
```
