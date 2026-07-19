# Action-name diagnostic audit

Static candidate audit; no model calls. The existing `name_only` label is a misnomer: the probe receives the oracle action-name sequence and guesses canonical arguments.

Observed: **69/200 (34.5%)**, Wilson 95% CI [28.3%, 41.3%], family bootstrap 95% CI [28.0%, 41.0%].
Uniform argument guessing: expected **27.75/200 (13.9%)**; Poisson-binomial tail p=8.29e-15.

Enum positions: {0: 194, 1: 107, 2: 101}. The index-0 majority baseline is identical to the implemented probe and also succeeds on 69/200.

## Interpretation

The diagnostic is above uniform argument chance, but its 34.5% rate equals the global first-enum-position majority baseline. It demonstrates combined oracle-name exposure and enum-order imbalance, not independently identified action-name leakage.

## Recommended paper correction

An oracle-name/canonical-argument diagnostic succeeds on 69/200 tasks (34.5%; report CI), versus 13.9% expected under uniform argument guessing. Because index 0 is the global enum-position majority and the probe is given the gold action names, this is a material combined interface/ordering leakage diagnostic, not evidence that action names alone solve 34.5%.

## By domain

| Stratum | n | success | Wilson 95% CI | uniform chance |
|---|---:|---:|---:|---:|
| commerce | 40 | 35.0% | [22.1%, 50.5%] | 15.1% |
| it | 40 | 32.5% | [20.1%, 48.0%] | 7.2% |
| procurement | 40 | 35.0% | [22.1%, 50.5%] | 9.3% |
| scheduling | 40 | 35.0% | [22.1%, 50.5%] | 20.0% |
| travel | 40 | 35.0% | [22.1%, 50.5%] | 17.8% |

## By sequence length

| Stratum | n | success | Wilson 95% CI | uniform chance |
|---|---:|---:|---:|---:|
| 1 | 38 | 36.8% | [23.4%, 52.7%] | 33.3% |
| 2 | 123 | 35.8% | [27.9%, 44.6%] | 11.1% |
| 3 | 38 | 28.9% | [17.0%, 44.8%] | 3.7% |
| 4 | 1 | 0.0% | [0.0%, 79.3%] | 1.2% |

## By enum position pattern

| Stratum | n | success | Wilson 95% CI | uniform chance |
|---|---:|---:|---:|---:|
| 0 | 14 | 100.0% | [78.5%, 100.0%] | 33.3% |
| 0,0 | 44 | 100.0% | [92.0%, 100.0%] | 11.1% |
| 0,0,0 | 11 | 100.0% | [74.1%, 100.0%] | 3.7% |
| 0,0,0,1 | 1 | 0.0% | [0.0%, 79.3%] | 1.2% |
| 0,0,1 | 2 | 0.0% | [0.0%, 65.8%] | 3.7% |
| 0,1 | 19 | 0.0% | [0.0%, 16.8%] | 11.1% |
| 0,2 | 33 | 0.0% | [0.0%, 10.4%] | 11.1% |
| 1 | 17 | 0.0% | [0.0%, 18.4%] | 33.3% |
| 1,1 | 13 | 0.0% | [0.0%, 22.8%] | 11.1% |
| 1,1,1 | 14 | 0.0% | [0.0%, 21.5%] | 3.7% |
| 2 | 7 | 0.0% | [0.0%, 35.4%] | 33.3% |
| 2,2 | 14 | 0.0% | [0.0%, 21.5%] | 11.1% |
| 2,2,2 | 11 | 0.0% | [0.0%, 25.9%] | 3.7% |

## Successful families (69)

- `cand_travel_001` / `travel_cancel_rebook_fee_consent` (travel; length 2; enum pattern 0,0)
- `cand_travel_004` / `travel_name_correction_document_match` (travel; length 2; enum pattern 0,0)
- `cand_travel_007` / `travel_award_ticket_miles_cash` (travel; length 2; enum pattern 0,0)
- `cand_travel_010` / `travel_wheelchair_connection_assistance` (travel; length 2; enum pattern 0,0)
- `cand_travel_013` / `travel_hotel_destination_supersession` (travel; length 1; enum pattern 0)
- `cand_travel_016` / `travel_overbooking_walk_remedy` (travel; length 2; enum pattern 0,0)
- `cand_travel_019` / `travel_car_driver_eligibility` (travel; length 1; enum pattern 0)
- `cand_travel_022` / `travel_ferry_vehicle_dimension` (travel; length 2; enum pattern 0,0)
- `cand_travel_025` / `travel_flight_credit_owner_binding` (travel; length 1; enum pattern 0)
- `cand_travel_028` / `travel_codeshare_operating_carrier_bag` (travel; length 1; enum pattern 0)
- `cand_travel_031` / `travel_tour_weather_cancellation` (travel; length 1; enum pattern 0)
- `cand_travel_034` / `travel_toll_transponder_region` (travel; length 1; enum pattern 0)
- `cand_travel_037` / `travel_group_booking_name_deadline` (travel; length 1; enum pattern 0)
- `cand_travel_040` / `travel_lost_ticket_reissue_identity` (travel; length 2; enum pattern 0,0)
- `cand_commerce_001` / `commerce_damaged_exchange_substitution` (commerce; length 2; enum pattern 0,0)
- `cand_commerce_004` / `commerce_warranty_repair_serial` (commerce; length 1; enum pattern 0)
- `cand_commerce_007` / `commerce_subscription_prorate_settlement` (commerce; length 3; enum pattern 0,0,0)
- `cand_commerce_010` / `commerce_coupon_stack_policy` (commerce; length 1; enum pattern 0)
- `cand_commerce_013` / `commerce_address_change_fulfillment_stage` (commerce; length 2; enum pattern 0,0)
- `cand_commerce_016` / `commerce_age_restricted_pickup` (commerce; length 2; enum pattern 0,0)
- `cand_commerce_019` / `commerce_digital_download_refund` (commerce; length 2; enum pattern 0,0)
- `cand_commerce_022` / `commerce_installation_service_dependency` (commerce; length 1; enum pattern 0)
- `cand_commerce_025` / `commerce_bundle_component_return` (commerce; length 2; enum pattern 0,0)
- `cand_commerce_028` / `commerce_tax_exemption_document` (commerce; length 2; enum pattern 0,0)
- `cand_commerce_031` / `commerce_furniture_delivery_stair_fee` (commerce; length 2; enum pattern 0,0)
- `cand_commerce_034` / `commerce_chargeback_open_refund_block` (commerce; length 1; enum pattern 0)
- `cand_commerce_037` / `commerce_device_activation_carrier_lock` (commerce; length 1; enum pattern 0)
- `cand_commerce_040` / `commerce_repair_data_backup_consent` (commerce; length 3; enum pattern 0,0,0)
- `cand_procurement_001` / `proc_competitive_bid_threshold` (procurement; length 2; enum pattern 0,0)
- `cand_procurement_004` / `proc_vendor_onboarding_tax` (procurement; length 2; enum pattern 0,0)
- `cand_procurement_007` / `proc_auto_renewal_notice` (procurement; length 2; enum pattern 0,0)
- `cand_procurement_010` / `proc_receipt_invoice_mismatch` (procurement; length 2; enum pattern 0,0)
- `cand_procurement_013` / `proc_blanket_po_depletion` (procurement; length 2; enum pattern 0,0)
- `cand_procurement_016` / `proc_insurance_certificate_expiry` (procurement; length 3; enum pattern 0,0,0)
- `cand_procurement_019` / `proc_prepaid_supplier_risk` (procurement; length 2; enum pattern 0,0)
- `cand_procurement_022` / `proc_delegation_limit` (procurement; length 2; enum pattern 0,0)
- `cand_procurement_025` / `proc_reverse_auction_reserve` (procurement; length 2; enum pattern 0,0)
- `cand_procurement_028` / `proc_preference_program_eligibility` (procurement; length 2; enum pattern 0,0)
- `cand_procurement_031` / `proc_consignment_title_transfer` (procurement; length 3; enum pattern 0,0,0)
- `cand_procurement_034` / `proc_custom_development_ip` (procurement; length 2; enum pattern 0,0)
- `cand_procurement_037` / `proc_cyber_insurance_limit` (procurement; length 2; enum pattern 0,0)
- `cand_procurement_040` / `proc_punchout_tax_jurisdiction` (procurement; length 2; enum pattern 0,0)
- `cand_it_003` / `it_breakglass_expiry` (it; length 2; enum pattern 0,0)
- `cand_it_006` / `it_backup_restore_scope` (it; length 3; enum pattern 0,0,0)
- `cand_it_009` / `it_database_failover_lag` (it; length 3; enum pattern 0,0,0)
- `cand_it_012` / `it_sso_metadata_rollover` (it; length 3; enum pattern 0,0,0)
- `cand_it_015` / `it_change_window_timezone` (it; length 2; enum pattern 0,0)
- `cand_it_018` / `it_kubernetes_namespace_quota` (it; length 2; enum pattern 0,0)
- `cand_it_021` / `it_license_reclamation_dependency` (it; length 2; enum pattern 0,0)
- `cand_it_024` / `it_monitoring_silence_scope` (it; length 2; enum pattern 0,0)
- `cand_it_027` / `it_kernel_rollout_hardware` (it; length 3; enum pattern 0,0,0)
- `cand_it_030` / `it_ci_runner_compromise` (it; length 3; enum pattern 0,0,0)
- `cand_it_033` / `it_ntp_drift_authentication` (it; length 3; enum pattern 0,0,0)
- `cand_it_036` / `it_shared_mailbox_delegation` (it; length 2; enum pattern 0,0)
- `cand_it_039` / `it_storage_key_rotation_replicas` (it; length 3; enum pattern 0,0,0)
- `cand_scheduling_001` / `scheduling_specialist_cancellation_offer` (scheduling; length 2; enum pattern 0,0)
- `cand_scheduling_004` / `scheduling_interview_candidate_confirmation` (scheduling; length 2; enum pattern 0,0)
- `cand_scheduling_007` / `scheduling_passport_document_clearance` (scheduling; length 1; enum pattern 0)
- `cand_scheduling_010` / `scheduling_cancellation_fee_acceptance` (scheduling; length 2; enum pattern 0,0)
- `cand_scheduling_013` / `scheduling_room_inventory_conflict` (scheduling; length 2; enum pattern 0,0)
- `cand_scheduling_016` / `scheduling_tenant_entry_authorization` (scheduling; length 2; enum pattern 0,0)
- `cand_scheduling_019` / `scheduling_childcare_authorized_pickup` (scheduling; length 1; enum pattern 0)
- `cand_scheduling_022` / `scheduling_onboarding_recording_consent` (scheduling; length 2; enum pattern 0,0)
- `cand_scheduling_025` / `scheduling_shift_swap_coverage` (scheduling; length 2; enum pattern 0,0)
- `cand_scheduling_028` / `scheduling_mediation_participant_authority` (scheduling; length 2; enum pattern 0,0)
- `cand_scheduling_031` / `scheduling_advising_queue_priority` (scheduling; length 2; enum pattern 0,0)
- `cand_scheduling_034` / `scheduling_venue_deposit_authority` (scheduling; length 2; enum pattern 0,0)
- `cand_scheduling_037` / `scheduling_language_class_waitlist` (scheduling; length 2; enum pattern 0,0)
- `cand_scheduling_040` / `scheduling_teleconference_recording_authority` (scheduling; length 2; enum pattern 0,0)
