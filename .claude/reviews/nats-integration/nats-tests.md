richardwoollcott@promaxgb10-41b1:~/Projects/appmilla_github/nats-infrastructure$ pip install pytest
error: externally-managed-environment

× This environment is externally managed
╰─> To install Python packages system-wide, try apt install
    python3-xyz, where xyz is the package you are trying to
    install.
    
    If you wish to install a non-Debian-packaged Python package,
    create a virtual environment using python3 -m venv path/to/venv.
    Then use path/to/venv/bin/python and path/to/venv/bin/pip. Make
    sure you have python3-full installed.
    
    If you wish to install a non-Debian packaged Python application,
    it may be easiest to use pipx install xyz, which will manage a
    virtual environment for you. Make sure you have pipx installed.
    
    See /usr/share/doc/python3.12/README.venv for more information.

note: If you believe this is a mistake, please contact your Python installation or OS distribution provider. You can override this, at the risk of breaking your Python installation or OS, by passing --break-system-packages.
hint: See PEP 668 for the detailed specification.
richardwoollcott@promaxgb10-41b1:~/Projects/appmilla_github/nats-infrastructure$ pytest tests/ -v
=================================================== test session starts ===================================================
platform linux -- Python 3.12.3, pytest-9.0.2, pluggy-1.6.0 -- /usr/bin/python3
cachedir: .pytest_cache
rootdir: /home/richardwoollcott/Projects/appmilla_github/nats-infrastructure
plugins: asyncio-1.3.0, anyio-4.12.1, cov-7.0.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 693 items                                                                                                       

tests/test_account_configs.py::TestTemplateFileExists::test_template_file_exists PASSED                             [  0%]
tests/test_account_configs.py::TestTemplateFileExists::test_template_file_is_not_empty PASSED                       [  0%]
tests/test_account_configs.py::TestTemplateFileExists::test_template_contains_appmilla_account PASSED               [  0%]
tests/test_account_configs.py::TestTemplateFileExists::test_template_contains_finproxy_account PASSED               [  0%]
tests/test_account_configs.py::TestTemplateFileExists::test_template_contains_sys_account PASSED                    [  0%]
tests/test_account_configs.py::TestTemplateVariables::test_rich_password_variable PASSED                            [  0%]
tests/test_account_configs.py::TestTemplateVariables::test_james_password_variable PASSED                           [  1%]
tests/test_account_configs.py::TestTemplateVariables::test_mark_password_variable PASSED                            [  1%]
tests/test_account_configs.py::TestTemplateVariables::test_admin_password_variable PASSED                           [  1%]
tests/test_account_configs.py::TestTemplateVariables::test_no_hardcoded_passwords PASSED                            [  1%]
tests/test_account_configs.py::TestAppmillaAccount::test_appmilla_has_rich_user PASSED                              [  1%]
tests/test_account_configs.py::TestAppmillaAccount::test_appmilla_has_james_user PASSED                             [  1%]
tests/test_account_configs.py::TestAppmillaAccount::test_appmilla_full_publish_access PASSED                        [  1%]
tests/test_account_configs.py::TestAppmillaAccount::test_appmilla_full_subscribe_access PASSED                      [  2%]
tests/test_account_configs.py::TestAppmillaAccount::test_appmilla_jetstream_enabled PASSED                          [  2%]
tests/test_account_configs.py::TestFinproxyAccount::test_finproxy_has_mark_user PASSED                              [  2%]
tests/test_account_configs.py::TestFinproxyAccount::test_finproxy_publish_scoped PASSED                             [  2%]
tests/test_account_configs.py::TestFinproxyAccount::test_finproxy_subscribe_scoped PASSED                           [  2%]
tests/test_account_configs.py::TestFinproxyAccount::test_finproxy_jetstream_enabled PASSED                          [  2%]
tests/test_account_configs.py::TestSysAccount::test_sys_has_admin_user PASSED                                       [  2%]
tests/test_account_configs.py::TestSysAccount::test_sys_designated_as_system_account PASSED                         [  3%]
tests/test_account_configs.py::TestDockerEntrypoint::test_entrypoint_file_exists PASSED                             [  3%]
tests/test_account_configs.py::TestDockerEntrypoint::test_entrypoint_is_executable PASSED                           [  3%]
tests/test_account_configs.py::TestDockerEntrypoint::test_entrypoint_has_shebang PASSED                             [  3%]
tests/test_account_configs.py::TestDockerEntrypoint::test_entrypoint_runs_envsubst PASSED                           [  3%]
tests/test_account_configs.py::TestDockerEntrypoint::test_entrypoint_execs_nats_server PASSED                       [  3%]
tests/test_account_configs.py::TestDockerEntrypoint::test_entrypoint_processes_template PASSED                      [  3%]
tests/test_account_configs.py::TestDockerEntrypoint::test_entrypoint_is_not_empty PASSED                            [  4%]
tests/test_account_configs.py::TestNoPlaintextPasswords::test_env_file_in_gitignore PASSED                          [  4%]
tests/test_account_configs.py::TestNoPlaintextPasswords::test_template_has_no_real_passwords PASSED                 [  4%]
tests/test_account_configs.py::TestNoPlaintextPasswords::test_no_generated_conf_committed PASSED                    [  4%]
tests/test_account_configs.py::TestTemplateSyntax::test_braces_balanced PASSED                                      [  4%]
tests/test_account_configs.py::TestTemplateSyntax::test_uses_nats_config_format PASSED                              [  4%]
tests/test_account_configs.py::TestTemplateSyntax::test_has_explanatory_comments PASSED                             [  4%]
tests/test_account_configs.py::TestTemplateSyntax::test_accounts_block_exists PASSED                                [  5%]
tests/test_docker_compose.py::TestComposeFileExists::test_compose_file_exists PASSED                                [  5%]
tests/test_docker_compose.py::TestComposeFileExists::test_compose_file_is_not_empty PASSED                          [  5%]
tests/test_docker_compose.py::TestComposeFileExists::test_compose_has_services_key PASSED                           [  5%]
tests/test_docker_compose.py::TestComposeFileExists::test_nats_service_defined PASSED                               [  5%]
tests/test_docker_compose.py::TestNatsImage::test_image_is_nats_2_11_alpine PASSED                                  [  5%]
tests/test_docker_compose.py::TestCustomEntrypoint::test_entrypoint_references_docker_entrypoint_sh PASSED          [  5%]
tests/test_docker_compose.py::TestNamedVolume::test_top_level_volumes_defines_nats_data PASSED                      [  6%]
tests/test_docker_compose.py::TestNamedVolume::test_nats_data_mounted_at_data_jetstream PASSED                      [  6%]
tests/test_docker_compose.py::TestHealthCheck::test_healthcheck_exists PASSED                                       [  6%]
tests/test_docker_compose.py::TestHealthCheck::test_healthcheck_test_command PASSED                                 [  6%]
tests/test_docker_compose.py::TestHealthCheck::test_healthcheck_has_start_period PASSED                             [  6%]
tests/test_docker_compose.py::TestHealthCheck::test_healthcheck_has_interval PASSED                                 [  6%]
tests/test_docker_compose.py::TestHealthCheck::test_healthcheck_has_timeout PASSED                                  [  6%]
tests/test_docker_compose.py::TestHealthCheck::test_healthcheck_has_retries PASSED                                  [  7%]
tests/test_docker_compose.py::TestRestartPolicy::test_restart_is_unless_stopped PASSED                              [  7%]
tests/test_docker_compose.py::TestPortExposure::test_port_4222_exposed PASSED                                       [  7%]
tests/test_docker_compose.py::TestPortExposure::test_port_8222_exposed PASSED                                       [  7%]
tests/test_docker_compose.py::TestCustomNetwork::test_top_level_networks_defines_ships_computer PASSED              [  7%]
tests/test_docker_compose.py::TestCustomNetwork::test_nats_service_uses_ships_computer_network PASSED               [  7%]
tests/test_docker_compose.py::TestConfigMountsReadOnly::test_config_mounted_read_only PASSED                        [  7%]
tests/test_docker_compose.py::TestEnvFile::test_env_file_references_dot_env PASSED                                  [  8%]
tests/test_dockerfile.py::TestDockerfileExists::test_dockerfile_exists PASSED                                       [  8%]
tests/test_dockerfile.py::TestDockerfileExists::test_dockerfile_is_not_empty PASSED                                 [  8%]
tests/test_dockerfile.py::TestDockerfileBaseImage::test_from_nats_alpine PASSED                                     [  8%]
tests/test_dockerfile.py::TestDockerfileGettext::test_apk_add_gettext PASSED                                        [  8%]
tests/test_dockerfile.py::TestDockerfileGettext::test_no_cache_flag PASSED                                          [  8%]
tests/test_dockerfile.py::TestDockerfileCopyEntrypoint::test_copy_entrypoint PASSED                                 [  8%]
tests/test_dockerfile.py::TestDockerfileCopyEntrypoint::test_chmod_entrypoint PASSED                                [  9%]
tests/test_dockerfile.py::TestDockerfileEntrypointCmd::test_entrypoint_set PASSED                                   [  9%]
tests/test_dockerfile.py::TestDockerfileEntrypointCmd::test_cmd_set PASSED                                          [  9%]
tests/test_dockerfile.py::TestDockerignore::test_dockerignore_exists PASSED                                         [  9%]
tests/test_dockerfile.py::TestDockerignore::test_excludes_required_directories[.git] PASSED                         [  9%]
tests/test_dockerfile.py::TestDockerignore::test_excludes_required_directories[docs/] PASSED                        [  9%]
tests/test_dockerfile.py::TestDockerignore::test_excludes_required_directories[tasks/] PASSED                       [  9%]
tests/test_dockerfile.py::TestDockerignore::test_excludes_required_directories[.claude/] PASSED                     [ 10%]
tests/test_dockerfile.py::TestDockerignore::test_excludes_required_directories[.guardkit/] PASSED                   [ 10%]
tests/test_dockerfile.py::TestDockerComposeBuildContext::test_compose_exists PASSED                                 [ 10%]
tests/test_dockerfile.py::TestDockerComposeBuildContext::test_uses_build_context PASSED                             [ 10%]
tests/test_dockerfile.py::TestDockerComposeBuildContext::test_no_image_directive_for_nats PASSED                    [ 10%]
tests/test_env_example.py::TestEnvExampleExists::test_env_example_file_exists PASSED                                [ 10%]
tests/test_env_example.py::TestEnvExampleExists::test_env_example_is_not_empty PASSED                               [ 10%]
tests/test_env_example.py::TestEnvExampleExists::test_env_example_at_repository_root PASSED                         [ 11%]
tests/test_env_example.py::TestPasswordVariables::test_variable_is_present[RICH_NATS_PASSWORD] PASSED               [ 11%]
tests/test_env_example.py::TestPasswordVariables::test_variable_is_present[JAMES_NATS_PASSWORD] PASSED              [ 11%]
tests/test_env_example.py::TestPasswordVariables::test_variable_is_present[MARK_NATS_PASSWORD] PASSED               [ 11%]
tests/test_env_example.py::TestPasswordVariables::test_variable_is_present[ADMIN_NATS_PASSWORD] PASSED              [ 11%]
tests/test_env_example.py::TestPasswordVariables::test_variable_has_placeholder_value[RICH_NATS_PASSWORD] PASSED    [ 11%]
tests/test_env_example.py::TestPasswordVariables::test_variable_has_placeholder_value[JAMES_NATS_PASSWORD] PASSED   [ 11%]
tests/test_env_example.py::TestPasswordVariables::test_variable_has_placeholder_value[MARK_NATS_PASSWORD] PASSED    [ 12%]
tests/test_env_example.py::TestPasswordVariables::test_variable_has_placeholder_value[ADMIN_NATS_PASSWORD] PASSED   [ 12%]
tests/test_env_example.py::TestPasswordVariables::test_all_four_variables_present PASSED                            [ 12%]
tests/test_env_example.py::TestPasswordVariables::test_no_real_passwords PASSED                                     [ 12%]
tests/test_env_example.py::TestVariableComments::test_has_comment_lines PASSED                                      [ 12%]
tests/test_env_example.py::TestVariableComments::test_variable_has_preceding_comment[RICH_NATS_PASSWORD] PASSED     [ 12%]
tests/test_env_example.py::TestVariableComments::test_variable_has_preceding_comment[JAMES_NATS_PASSWORD] PASSED    [ 12%]
tests/test_env_example.py::TestVariableComments::test_variable_has_preceding_comment[MARK_NATS_PASSWORD] PASSED     [ 13%]
tests/test_env_example.py::TestVariableComments::test_variable_has_preceding_comment[ADMIN_NATS_PASSWORD] PASSED    [ 13%]
tests/test_env_example.py::TestVariableComments::test_comments_mention_account_names PASSED                         [ 13%]
tests/test_env_example.py::TestVariableComments::test_comments_mention_no_default PASSED                            [ 13%]
tests/test_env_example.py::TestGitignore::test_env_in_gitignore PASSED                                              [ 13%]
tests/test_env_example.py::TestGitignore::test_env_example_not_in_gitignore PASSED                                  [ 13%]
tests/test_env_example.py::TestSetupGuideReference::test_readme_references_env_example PASSED                       [ 13%]
tests/test_env_example.py::TestSetupGuideReference::test_readme_mentions_copy_step PASSED                           [ 14%]
tests/test_env_example.py::TestSetupGuideReference::test_env_example_self_documents_setup PASSED                    [ 14%]
tests/test_env_example.py::TestConsistencyWithTemplate::test_variables_match_template_references PASSED             [ 14%]
tests/test_env_example.py::TestConsistencyWithTemplate::test_variables_match_entrypoint_validation PASSED           [ 14%]
tests/test_kv_definitions.py::TestKvDefsFileExists::test_file_exists PASSED                                         [ 14%]
tests/test_kv_definitions.py::TestKvDefsFileExists::test_file_is_not_empty PASSED                                   [ 14%]
tests/test_kv_definitions.py::TestKvDefsFileExists::test_file_in_kv_directory PASSED                                [ 15%]
tests/test_kv_definitions.py::TestKvDefsFileExists::test_json_is_parseable PASSED                                   [ 15%]
tests/test_kv_definitions.py::TestKvDefsFileExists::test_has_kv_buckets_key PASSED                                  [ 15%]
tests/test_kv_definitions.py::TestKvDefsFileExists::test_kv_buckets_is_array PASSED                                 [ 15%]
tests/test_kv_definitions.py::TestKvBucketDefinitions::test_exactly_4_kv_buckets PASSED                             [ 15%]
tests/test_kv_definitions.py::TestKvBucketDefinitions::test_all_expected_buckets_present PASSED                     [ 15%]
tests/test_kv_definitions.py::TestKvBucketDefinitions::test_no_duplicate_bucket_names PASSED                        [ 15%]
tests/test_kv_definitions.py::TestKvBucketDefinitions::test_all_buckets_have_required_fields PASSED                 [ 16%]
tests/test_kv_definitions.py::TestKvBucketDefinitions::test_name_is_string PASSED                                   [ 16%]
tests/test_kv_definitions.py::TestKvBucketDefinitions::test_description_is_string PASSED                            [ 16%]
tests/test_kv_definitions.py::TestKvBucketDefinitions::test_description_is_not_empty PASSED                         [ 16%]
tests/test_kv_definitions.py::TestKvBucketDefinitions::test_history_is_integer PASSED                               [ 16%]
tests/test_kv_definitions.py::TestKvBucketDefinitions::test_max_value_size_is_string PASSED                         [ 16%]
tests/test_kv_definitions.py::TestKvBucketDefinitions::test_storage_is_string PASSED                                [ 16%]
tests/test_kv_definitions.py::TestKvBucketDefinitions::test_description_contains_expected_keyword[agent-status] PASSED [ 17%]
tests/test_kv_definitions.py::TestKvBucketDefinitions::test_description_contains_expected_keyword[agent-registry] PASSED [ 17%]
tests/test_kv_definitions.py::TestKvBucketDefinitions::test_description_contains_expected_keyword[pipeline-state] PASSED [ 17%]
tests/test_kv_definitions.py::TestKvBucketDefinitions::test_description_contains_expected_keyword[jarvis-session] PASSED [ 17%]
tests/test_kv_definitions.py::TestKvBucketTtlFormat::test_ttl_is_string PASSED                                      [ 17%]
tests/test_kv_definitions.py::TestKvBucketTtlFormat::test_ttl_is_empty_or_valid_duration PASSED                     [ 17%]
tests/test_kv_definitions.py::TestKvBucketTtlFormat::test_expected_ttl_values[agent-status] PASSED                  [ 17%]
tests/test_kv_definitions.py::TestKvBucketTtlFormat::test_expected_ttl_values[agent-registry] PASSED                [ 18%]
tests/test_kv_definitions.py::TestKvBucketTtlFormat::test_expected_ttl_values[pipeline-state] PASSED                [ 18%]
tests/test_kv_definitions.py::TestKvBucketTtlFormat::test_expected_ttl_values[jarvis-session] PASSED                [ 18%]
tests/test_kv_definitions.py::TestKvBucketTtlFormat::test_agent_status_no_ttl PASSED                                [ 18%]
tests/test_kv_definitions.py::TestKvBucketTtlFormat::test_agent_registry_no_ttl PASSED                              [ 18%]
tests/test_kv_definitions.py::TestKvBucketTtlFormat::test_pipeline_state_ttl_is_7d PASSED                           [ 18%]
tests/test_kv_definitions.py::TestKvBucketTtlFormat::test_jarvis_session_ttl_is_1h PASSED                           [ 18%]
tests/test_kv_definitions.py::TestKvBucketStorageTypes::test_storage_is_valid_type PASSED                           [ 19%]
tests/test_kv_definitions.py::TestKvBucketStorageTypes::test_agent_status_storage_is_file PASSED                    [ 19%]
tests/test_kv_definitions.py::TestKvBucketStorageTypes::test_agent_registry_storage_is_file PASSED                  [ 19%]
tests/test_kv_definitions.py::TestKvBucketStorageTypes::test_pipeline_state_storage_is_file PASSED                  [ 19%]
tests/test_kv_definitions.py::TestKvBucketStorageTypes::test_jarvis_session_storage_is_memory PASSED                [ 19%]
tests/test_kv_definitions.py::TestKvBucketStorageTypes::test_expected_storage_values[agent-status] PASSED           [ 19%]
tests/test_kv_definitions.py::TestKvBucketStorageTypes::test_expected_storage_values[agent-registry] PASSED         [ 19%]
tests/test_kv_definitions.py::TestKvBucketStorageTypes::test_expected_storage_values[pipeline-state] PASSED         [ 20%]
tests/test_kv_definitions.py::TestKvBucketStorageTypes::test_expected_storage_values[jarvis-session] PASSED         [ 20%]
tests/test_kv_definitions.py::TestKvBucketHistoryDepth::test_history_is_positive_integer PASSED                     [ 20%]
tests/test_kv_definitions.py::TestKvBucketHistoryDepth::test_agent_status_history_is_1 PASSED                       [ 20%]
tests/test_kv_definitions.py::TestKvBucketHistoryDepth::test_agent_registry_history_is_5 PASSED                     [ 20%]
tests/test_kv_definitions.py::TestKvBucketHistoryDepth::test_pipeline_state_history_is_3 PASSED                     [ 20%]
tests/test_kv_definitions.py::TestKvBucketHistoryDepth::test_jarvis_session_history_is_1 PASSED                     [ 20%]
tests/test_kv_definitions.py::TestKvBucketHistoryDepth::test_expected_history_values[agent-status] PASSED           [ 21%]
tests/test_kv_definitions.py::TestKvBucketHistoryDepth::test_expected_history_values[agent-registry] PASSED         [ 21%]
tests/test_kv_definitions.py::TestKvBucketHistoryDepth::test_expected_history_values[pipeline-state] PASSED         [ 21%]
tests/test_kv_definitions.py::TestKvBucketHistoryDepth::test_expected_history_values[jarvis-session] PASSED         [ 21%]
tests/test_kv_definitions.py::TestKvDefsStyleConsistency::test_top_level_is_object_with_array_value PASSED          [ 21%]
tests/test_kv_definitions.py::TestKvDefsStyleConsistency::test_each_bucket_is_object PASSED                         [ 21%]
tests/test_kv_definitions.py::TestKvDefsStyleConsistency::test_bucket_names_are_kebab_case PASSED                   [ 21%]
tests/test_kv_definitions.py::TestKvDefsStyleConsistency::test_all_buckets_have_replicas_field PASSED               [ 22%]
tests/test_kv_definitions.py::TestKvDefsStyleConsistency::test_all_replicas_are_1 PASSED                            [ 22%]
tests/test_kv_definitions.py::TestKvDefsStyleConsistency::test_all_buckets_have_description PASSED                  [ 22%]
tests/test_kv_definitions.py::TestKvBucketMaxValueSize::test_max_value_size_format PASSED                           [ 22%]
tests/test_kv_definitions.py::TestKvBucketMaxValueSize::test_expected_max_value_size[agent-status] PASSED           [ 22%]
tests/test_kv_definitions.py::TestKvBucketMaxValueSize::test_expected_max_value_size[agent-registry] PASSED         [ 22%]
tests/test_kv_definitions.py::TestKvBucketMaxValueSize::test_expected_max_value_size[pipeline-state] PASSED         [ 22%]
tests/test_kv_definitions.py::TestKvBucketMaxValueSize::test_expected_max_value_size[jarvis-session] PASSED         [ 23%]
tests/test_kv_definitions.py::TestKvDefinitionsContract::test_file_exists_at_expected_path PASSED                   [ 23%]
tests/test_kv_definitions.py::TestKvDefinitionsContract::test_top_level_kv_buckets_key_exists PASSED                [ 23%]
tests/test_kv_definitions.py::TestKvDefinitionsContract::test_at_least_4_kv_buckets PASSED                          [ 23%]
tests/test_kv_definitions.py::TestKvDefinitionsContract::test_all_buckets_have_required_fields PASSED               [ 23%]
tests/test_kv_watch_integration.py::TestKvBucketsCreated::test_provision_script_creates_all_buckets SKIPPED (NA...) [ 23%]
tests/test_kv_watch_integration.py::TestKvBucketsCreated::test_bucket_info_accessible[agent-status] SKIPPED (NA...) [ 23%]
tests/test_kv_watch_integration.py::TestKvBucketsCreated::test_bucket_info_accessible[agent-registry] SKIPPED (...) [ 24%]
tests/test_kv_watch_integration.py::TestKvBucketsCreated::test_bucket_info_accessible[pipeline-state] SKIPPED (...) [ 24%]
tests/test_kv_watch_integration.py::TestKvBucketsCreated::test_bucket_info_accessible[jarvis-session] SKIPPED (...) [ 24%]
tests/test_kv_watch_integration.py::TestKvBucketsCreated::test_agent_status_storage_is_file SKIPPED (NATS serve...) [ 24%]
tests/test_kv_watch_integration.py::TestKvBucketsCreated::test_agent_registry_history_is_5 SKIPPED (NATS server...) [ 24%]
tests/test_kv_watch_integration.py::TestKvBucketsCreated::test_jarvis_session_storage_is_memory SKIPPED (NATS s...) [ 24%]
tests/test_kv_watch_integration.py::TestKvBucketsCreated::test_pipeline_state_storage_is_file SKIPPED (NATS ser...) [ 24%]
tests/test_kv_watch_integration.py::TestAgentStatusPutGet::test_put_and_get_roundtrip SKIPPED (NATS server not ...) [ 25%]
tests/test_kv_watch_integration.py::TestAgentStatusPutGet::test_update_and_get_latest SKIPPED (NATS server not ...) [ 25%]
tests/test_kv_watch_integration.py::TestAgentStatusWatch::test_watch_receives_put_update SKIPPED (NATS server n...) [ 25%]
tests/test_kv_watch_integration.py::TestAgentStatusWatch::test_watch_receives_multiple_updates SKIPPED (NATS se...) [ 25%]
tests/test_kv_watch_integration.py::TestAgentRegistryHistoryDepth::test_history_depth_limited_to_5 SKIPPED (NAT...) [ 25%]
tests/test_kv_watch_integration.py::TestAgentRegistryHistoryDepth::test_latest_value_is_most_recent SKIPPED (NA...) [ 25%]
tests/test_kv_watch_integration.py::TestAgentRegistryHistoryDepth::test_oldest_history_entry_is_v2_not_v1 SKIPPED   [ 25%]
tests/test_kv_watch_integration.py::TestJarvisSessionTtlExpiry::test_production_bucket_has_1h_ttl SKIPPED (NATS...) [ 26%]
tests/test_kv_watch_integration.py::TestJarvisSessionTtlExpiry::test_put_and_get_before_expiry SKIPPED (NATS se...) [ 26%]
tests/test_kv_watch_integration.py::TestJarvisSessionTtlExpiry::test_short_ttl_bucket_expiry SKIPPED (NATS serv...) [ 26%]
tests/test_kv_watch_integration.py::TestPipelineStatePersistence::test_value_persists_across_broker_restart SKIPPED [ 26%]
tests/test_kv_watch_integration.py::TestProvisionKvDryRun::test_dry_run_produces_output SKIPPED (NATS server no...) [ 26%]
tests/test_kv_watch_integration.py::TestProvisionKvDryRun::test_dry_run_lists_all_buckets SKIPPED (NATS server ...) [ 26%]
tests/test_kv_watch_integration.py::TestProvisionKvDryRun::test_dry_run_shows_dry_run_prefix SKIPPED (NATS serv...) [ 26%]
tests/test_kv_watch_integration.py::TestProvisionKvDryRun::test_dry_run_does_not_connect_to_nats SKIPPED (NATS ...) [ 27%]
tests/test_kv_watch_integration.py::TestProvisionKvDryRun::test_dry_run_shows_processing_count SKIPPED (NATS se...) [ 27%]
tests/test_kv_watch_integration.py::TestProvisionKvDryRun::test_dry_run_shows_summary SKIPPED (NATS server not ...) [ 27%]
tests/test_kv_watch_integration.py::TestAllTestsPass::test_nats_server_is_healthy SKIPPED (NATS server not avai...) [ 27%]
tests/test_kv_watch_integration.py::TestAllTestsPass::test_all_expected_buckets_are_operational SKIPPED (NATS s...) [ 27%]
tests/test_nats_server_conf.py::TestConfigFileExists::test_config_file_exists PASSED                                [ 27%]
tests/test_nats_server_conf.py::TestConfigFileExists::test_config_file_is_not_empty PASSED                          [ 27%]
tests/test_nats_server_conf.py::TestConfigFileExists::test_server_name_is_ships_computer PASSED                     [ 28%]
tests/test_nats_server_conf.py::TestConfigFileExists::test_max_payload_is_1mb PASSED                                [ 28%]
tests/test_nats_server_conf.py::TestConfigFileExists::test_debug_disabled PASSED                                    [ 28%]
tests/test_nats_server_conf.py::TestConfigFileExists::test_trace_disabled PASSED                                    [ 28%]
tests/test_nats_server_conf.py::TestJetStreamConfiguration::test_jetstream_block_exists PASSED                      [ 28%]
tests/test_nats_server_conf.py::TestJetStreamConfiguration::test_jetstream_store_dir PASSED                         [ 28%]
tests/test_nats_server_conf.py::TestJetStreamConfiguration::test_jetstream_max_mem PASSED                           [ 29%]
tests/test_nats_server_conf.py::TestJetStreamConfiguration::test_jetstream_max_file PASSED                          [ 29%]
tests/test_nats_server_conf.py::TestNetworkBindings::test_client_port_4222 PASSED                                   [ 29%]
tests/test_nats_server_conf.py::TestNetworkBindings::test_client_listen_address PASSED                              [ 29%]
tests/test_nats_server_conf.py::TestNetworkBindings::test_monitoring_port_8222 PASSED                               [ 29%]
tests/test_nats_server_conf.py::TestNetworkBindings::test_monitoring_bind_address PASSED                            [ 29%]
tests/test_nats_server_conf.py::TestIncludeDirective::test_include_accounts_conf PASSED                             [ 29%]
tests/test_nats_server_conf.py::TestConfigComments::test_has_comment_lines PASSED                                   [ 30%]
tests/test_nats_server_conf.py::TestConfigComments::test_has_jetstream_section_comment PASSED                       [ 30%]
tests/test_nats_server_conf.py::TestConfigComments::test_has_logging_section_comment PASSED                         [ 30%]
tests/test_nats_server_conf.py::TestConfigSyntax::test_braces_balanced PASSED                                       [ 30%]
tests/test_nats_server_conf.py::TestConfigSyntax::test_no_json_syntax PASSED                                        [ 30%]
tests/test_nats_server_conf.py::TestConfigSyntax::test_uses_nats_config_format PASSED                               [ 30%]
tests/test_nats_server_conf.py::TestLoggingConfiguration::test_log_file_path PASSED                                 [ 30%]
tests/test_nats_server_conf.py::TestLoggingConfiguration::test_logtime_enabled PASSED                               [ 31%]
tests/test_provision_kv.py::TestScriptExistsAndExecutable::test_script_file_exists PASSED                           [ 31%]
tests/test_provision_kv.py::TestScriptExistsAndExecutable::test_script_is_executable PASSED                         [ 31%]
tests/test_provision_kv.py::TestScriptExistsAndExecutable::test_script_has_shebang PASSED                           [ 31%]
tests/test_provision_kv.py::TestScriptExistsAndExecutable::test_script_is_not_empty PASSED                          [ 31%]
tests/test_provision_kv.py::TestScriptExistsAndExecutable::test_uses_set_euo_pipefail PASSED                        [ 31%]
tests/test_provision_kv.py::TestReadsKvDefinitions::test_reads_kv_definitions_json PASSED                           [ 31%]
tests/test_provision_kv.py::TestReadsKvDefinitions::test_uses_jq_to_parse PASSED                                    [ 32%]
tests/test_provision_kv.py::TestReadsKvDefinitions::test_iterates_over_kv_buckets PASSED                            [ 32%]
tests/test_provision_kv.py::TestReadsKvDefinitions::test_extracts_bucket_name PASSED                                [ 32%]
tests/test_provision_kv.py::TestReadsKvDefinitions::test_extracts_bucket_ttl PASSED                                 [ 32%]
tests/test_provision_kv.py::TestReadsKvDefinitions::test_extracts_bucket_storage PASSED                             [ 32%]
tests/test_provision_kv.py::TestReadsKvDefinitions::test_extracts_bucket_history PASSED                             [ 32%]
tests/test_provision_kv.py::TestReadsKvDefinitions::test_extracts_bucket_max_value_size PASSED                      [ 32%]
tests/test_provision_kv.py::TestReadsKvDefinitions::test_extracts_bucket_replicas PASSED                            [ 33%]
tests/test_provision_kv.py::TestDryRunFlag::test_supports_dry_run_flag PASSED                                       [ 33%]
tests/test_provision_kv.py::TestDryRunFlag::test_dry_run_prevents_modification PASSED                               [ 33%]
tests/test_provision_kv.py::TestDryRunFlag::test_dry_run_shows_would_actions PASSED                                 [ 33%]
tests/test_provision_kv.py::TestDryRunFlag::test_dry_run_skips_nats_health_wait PASSED                              [ 33%]
tests/test_provision_kv.py::TestIdempotency::test_uses_nats_kv_info PASSED                                          [ 33%]
tests/test_provision_kv.py::TestIdempotency::test_uses_nats_kv_add PASSED                                           [ 33%]
tests/test_provision_kv.py::TestIdempotency::test_uses_nats_kv_update PASSED                                        [ 34%]
tests/test_provision_kv.py::TestIdempotency::test_has_provision_kv_bucket_function PASSED                           [ 34%]
tests/test_provision_kv.py::TestIdempotency::test_checks_existence_before_create PASSED                             [ 34%]
tests/test_provision_kv.py::TestNatsHealthCheck::test_has_wait_for_nats_function PASSED                             [ 34%]
tests/test_provision_kv.py::TestNatsHealthCheck::test_has_retry_mechanism PASSED                                    [ 34%]
tests/test_provision_kv.py::TestNatsHealthCheck::test_has_timeout_for_health_check PASSED                           [ 34%]
tests/test_provision_kv.py::TestNatsHealthCheck::test_uses_nats_server_check PASSED                                 [ 34%]
tests/test_provision_kv.py::TestNatsHealthCheck::test_fatal_exit_on_health_timeout PASSED                           [ 35%]
tests/test_provision_kv.py::TestNatsConnectionConfig::test_supports_nats_url_env_var PASSED                         [ 35%]
tests/test_provision_kv.py::TestNatsConnectionConfig::test_nats_url_default_localhost PASSED                        [ 35%]
tests/test_provision_kv.py::TestNatsConnectionConfig::test_supports_nats_creds_env_var PASSED                       [ 35%]
tests/test_provision_kv.py::TestNatsConnectionConfig::test_nats_creds_is_optional PASSED                            [ 35%]
tests/test_provision_kv.py::TestNatsConnectionConfig::test_builds_nats_opts_array PASSED                            [ 35%]
tests/test_provision_kv.py::TestSummaryOutput::test_tracks_created_count PASSED                                     [ 35%]
tests/test_provision_kv.py::TestSummaryOutput::test_tracks_updated_count PASSED                                     [ 36%]
tests/test_provision_kv.py::TestSummaryOutput::test_tracks_current_count PASSED                                     [ 36%]
tests/test_provision_kv.py::TestSummaryOutput::test_tracks_error_count PASSED                                       [ 36%]
tests/test_provision_kv.py::TestSummaryOutput::test_prints_summary_line PASSED                                      [ 36%]
tests/test_provision_kv.py::TestSummaryOutput::test_warns_on_errors PASSED                                          [ 36%]
tests/test_provision_kv.py::TestPrerequisiteChecks::test_checks_jq_available PASSED                                 [ 36%]
tests/test_provision_kv.py::TestPrerequisiteChecks::test_checks_nats_available PASSED                               [ 36%]
tests/test_provision_kv.py::TestPrerequisiteChecks::test_fatal_exit_if_jq_missing PASSED                            [ 37%]
tests/test_provision_kv.py::TestPrerequisiteChecks::test_fatal_exit_if_nats_missing PASSED                          [ 37%]
tests/test_provision_kv.py::TestPrerequisiteChecks::test_checks_definitions_file_exists PASSED                      [ 37%]
tests/test_provision_kv.py::TestShellcheck::test_script_passes_shellcheck SKIPPED (shellcheck not installed — i...) [ 37%]
tests/test_provision_kv.py::TestShellcheck::test_script_passes_shellcheck_warnings SKIPPED (shellcheck not inst...) [ 37%]
tests/test_provision_kv.py::TestLogFormat::test_all_log_prefixes_present PASSED                                     [ 37%]
tests/test_provision_kv.py::TestLogFormat::test_log_prefix_includes_bucket_name PASSED                              [ 37%]
tests/test_provision_kv.py::TestKvFlagSupport::test_supports_ttl_flag PASSED                                        [ 38%]
tests/test_provision_kv.py::TestKvFlagSupport::test_supports_history_flag PASSED                                    [ 38%]
tests/test_provision_kv.py::TestKvFlagSupport::test_supports_storage_flag PASSED                                    [ 38%]
tests/test_provision_kv.py::TestKvFlagSupport::test_supports_max_value_size_flag PASSED                             [ 38%]
tests/test_provision_kv.py::TestKvFlagSupport::test_supports_replicas_flag PASSED                                   [ 38%]
tests/test_provision_kv.py::TestKvFlagSupport::test_handles_empty_ttl PASSED                                        [ 38%]
tests/test_provision_kv.py::TestKvFlagSupport::test_ttl_is_conditional PASSED                                       [ 38%]
tests/test_provision_kv.py::TestScriptStructure::test_has_main_function PASSED                                      [ 39%]
tests/test_provision_kv.py::TestScriptStructure::test_calls_main_at_end PASSED                                      [ 39%]
tests/test_provision_kv.py::TestScriptStructure::test_has_exit_zero_on_success PASSED                               [ 39%]
tests/test_provision_kv.py::TestScriptStructure::test_has_exit_nonzero_on_fatal PASSED                              [ 39%]
tests/test_provision_streams.py::TestScriptExistsAndExecutable::test_script_file_exists PASSED                      [ 39%]
tests/test_provision_streams.py::TestScriptExistsAndExecutable::test_script_is_executable PASSED                    [ 39%]
tests/test_provision_streams.py::TestScriptExistsAndExecutable::test_script_has_shebang PASSED                      [ 39%]
tests/test_provision_streams.py::TestScriptExistsAndExecutable::test_script_is_not_empty PASSED                     [ 40%]
tests/test_provision_streams.py::TestStrictErrorHandling::test_uses_set_euo_pipefail PASSED                         [ 40%]
tests/test_provision_streams.py::TestShellcheck::test_script_passes_shellcheck SKIPPED (shellcheck not installe...) [ 40%]
tests/test_provision_streams.py::TestShellcheck::test_script_passes_shellcheck_warnings SKIPPED (shellcheck not...) [ 40%]
tests/test_provision_streams.py::TestReadsStreamDefinitions::test_reads_stream_definitions_json PASSED              [ 40%]
tests/test_provision_streams.py::TestReadsStreamDefinitions::test_uses_jq_to_parse PASSED                           [ 40%]
tests/test_provision_streams.py::TestReadsStreamDefinitions::test_checks_jq_available PASSED                        [ 40%]
tests/test_provision_streams.py::TestReadsStreamDefinitions::test_iterates_over_streams PASSED                      [ 41%]
tests/test_provision_streams.py::TestReadsStreamDefinitions::test_extracts_stream_name PASSED                       [ 41%]
tests/test_provision_streams.py::TestReadsStreamDefinitions::test_extracts_subjects PASSED                          [ 41%]
tests/test_provision_streams.py::TestReadsStreamDefinitions::test_extracts_retention PASSED                         [ 41%]
tests/test_provision_streams.py::TestReadsStreamDefinitions::test_extracts_max_age PASSED                           [ 41%]
tests/test_provision_streams.py::TestReadsStreamDefinitions::test_extracts_max_msgs PASSED                          [ 41%]
tests/test_provision_streams.py::TestReadsStreamDefinitions::test_extracts_storage PASSED                           [ 41%]
tests/test_provision_streams.py::TestReadsStreamDefinitions::test_extracts_replicas PASSED                          [ 42%]
tests/test_provision_streams.py::TestStreamCreation::test_uses_nats_stream_add PASSED                               [ 42%]
tests/test_provision_streams.py::TestStreamCreation::test_uses_defaults_flag PASSED                                 [ 42%]
tests/test_provision_streams.py::TestStreamCreation::test_logs_create_action PASSED                                 [ 42%]
tests/test_provision_streams.py::TestStreamCreation::test_checks_stream_existence_before_create PASSED              [ 42%]
tests/test_provision_streams.py::TestIdempotencyDetection::test_logs_ok_for_current_streams PASSED                  [ 42%]
tests/test_provision_streams.py::TestIdempotencyDetection::test_logs_update_for_changed_streams PASSED              [ 43%]
tests/test_provision_streams.py::TestStreamUpdate::test_uses_nats_stream_update PASSED                              [ 43%]
tests/test_provision_streams.py::TestStreamUpdate::test_uses_force_flag PASSED                                      [ 43%]
tests/test_provision_streams.py::TestStreamUpdate::test_logs_error_on_update_failure PASSED                         [ 43%]
tests/test_provision_streams.py::TestDryRunFlag::test_supports_dry_run_flag PASSED                                  [ 43%]
tests/test_provision_streams.py::TestDryRunFlag::test_dry_run_prevents_modification PASSED                          [ 43%]
tests/test_provision_streams.py::TestDryRunFlag::test_dry_run_shows_would_actions PASSED                            [ 43%]
tests/test_provision_streams.py::TestExitCodeBehavior::test_has_exit_zero_on_success PASSED                         [ 44%]
tests/test_provision_streams.py::TestExitCodeBehavior::test_has_exit_nonzero_on_fatal PASSED                        [ 44%]
tests/test_provision_streams.py::TestExitCodeBehavior::test_continues_after_nonfatal_errors PASSED                  [ 44%]
tests/test_provision_streams.py::TestNatsConnectionConfig::test_supports_nats_url_env_var PASSED                    [ 44%]
tests/test_provision_streams.py::TestNatsConnectionConfig::test_nats_url_default_localhost PASSED                   [ 44%]
tests/test_provision_streams.py::TestNatsConnectionConfig::test_supports_nats_creds_env_var PASSED                  [ 44%]
tests/test_provision_streams.py::TestNatsConnectionConfig::test_nats_creds_is_optional PASSED                       [ 44%]
tests/test_provision_streams.py::TestNatsHealthCheck::test_waits_for_nats PASSED                                    [ 45%]
tests/test_provision_streams.py::TestNatsHealthCheck::test_has_retry_mechanism PASSED                               [ 45%]
tests/test_provision_streams.py::TestNatsHealthCheck::test_has_timeout_for_health_check PASSED                      [ 45%]
tests/test_provision_streams.py::TestSummaryOutput::test_tracks_created_count PASSED                                [ 45%]
tests/test_provision_streams.py::TestSummaryOutput::test_tracks_updated_count PASSED                                [ 45%]
tests/test_provision_streams.py::TestSummaryOutput::test_tracks_current_count PASSED                                [ 45%]
tests/test_provision_streams.py::TestSummaryOutput::test_tracks_error_count PASSED                                  [ 45%]
tests/test_provision_streams.py::TestSummaryOutput::test_prints_summary_line PASSED                                 [ 46%]
tests/test_provision_streams.py::TestLogFormat::test_all_log_prefixes_present PASSED                                [ 46%]
tests/test_provision_streams.py::TestLogFormat::test_log_prefix_includes_stream_name PASSED                         [ 46%]
tests/test_provision_streams.py::TestStreamDefinitionsContract::test_top_level_streams_key_exists PASSED            [ 46%]
tests/test_provision_streams.py::TestStreamDefinitionsContract::test_at_least_7_streams PASSED                      [ 46%]
tests/test_provision_streams.py::TestStreamDefinitionsContract::test_all_streams_have_required_fields PASSED        [ 46%]
tests/test_provision_streams.py::TestStreamDefinitionsContract::test_retention_values_are_valid PASSED              [ 46%]
tests/test_provision_streams.py::TestKvBucketProvisioning::test_uses_nats_kv_add PASSED                             [ 47%]
tests/test_provision_streams.py::TestKvBucketProvisioning::test_uses_nats_kv_info PASSED                            [ 47%]
tests/test_provision_streams.py::TestKvBucketProvisioning::test_uses_nats_kv_update PASSED                          [ 47%]
tests/test_provision_streams.py::TestKvBucketProvisioning::test_reads_kv_buckets_from_json PASSED                   [ 47%]
tests/test_provision_streams.py::TestKvBucketProvisioning::test_extracts_kv_bucket_name PASSED                      [ 47%]
tests/test_provision_streams.py::TestKvBucketProvisioning::test_extracts_kv_bucket_ttl PASSED                       [ 47%]
tests/test_provision_streams.py::TestKvBucketProvisioning::test_has_provision_kv_bucket_function PASSED             [ 47%]
tests/test_provision_streams.py::TestKvBucketProvisioning::test_kv_bucket_section_after_streams PASSED              [ 48%]
tests/test_provision_streams.py::TestKvBucketIdempotency::test_checks_kv_existence_before_create PASSED             [ 48%]
tests/test_provision_streams.py::TestKvBucketIdempotency::test_logs_kv_create_action PASSED                         [ 48%]
tests/test_provision_streams.py::TestKvBucketIdempotency::test_logs_kv_ok_action PASSED                             [ 48%]
tests/test_provision_streams.py::TestKvBucketIdempotency::test_logs_kv_update_action PASSED                         [ 48%]
tests/test_provision_streams.py::TestKvBucketIdempotency::test_logs_kv_error_action PASSED                          [ 48%]
tests/test_provision_streams.py::TestKvBucketIdempotency::test_kv_dry_run_support PASSED                            [ 48%]
tests/test_provision_streams.py::TestKvBucketTtlProvisioning::test_supports_ttl_flag PASSED                         [ 49%]
tests/test_provision_streams.py::TestKvBucketTtlProvisioning::test_handles_null_ttl PASSED                          [ 49%]
tests/test_provision_streams.py::TestKvBucketTtlProvisioning::test_ttl_is_conditional PASSED                        [ 49%]
tests/test_provision_streams.py::TestKvBucketSummary::test_tracks_kv_created_count PASSED                           [ 49%]
tests/test_provision_streams.py::TestKvBucketSummary::test_tracks_kv_updated_count PASSED                           [ 49%]
tests/test_provision_streams.py::TestKvBucketSummary::test_tracks_kv_current_count PASSED                           [ 49%]
tests/test_provision_streams.py::TestKvBucketSummary::test_tracks_kv_error_count PASSED                             [ 49%]
tests/test_provision_streams.py::TestKvBucketSummary::test_prints_kv_summary_line PASSED                            [ 50%]
tests/test_readme.py::TestQuickStartSection::test_readme_exists PASSED                                              [ 50%]
tests/test_readme.py::TestQuickStartSection::test_readme_is_not_empty PASSED                                        [ 50%]
tests/test_readme.py::TestQuickStartSection::test_has_quick_start_section PASSED                                    [ 50%]
tests/test_readme.py::TestQuickStartSection::test_quick_start_has_docker_compose_up PASSED                          [ 50%]
tests/test_readme.py::TestQuickStartSection::test_quick_start_has_build_flag PASSED                                 [ 50%]
tests/test_readme.py::TestQuickStartSection::test_quick_start_has_env_copy PASSED                                   [ 50%]
tests/test_readme.py::TestQuickStartSection::test_quick_start_has_verify_script PASSED                              [ 51%]
tests/test_readme.py::TestQuickStartSection::test_no_obsolete_setup_gb10_reference PASSED                           [ 51%]
tests/test_readme.py::TestQuickStartSection::test_provision_streams_reference_in_streams_section PASSED             [ 51%]
tests/test_readme.py::TestVolumeManagementSection::test_has_volume_management_section PASSED                        [ 51%]
tests/test_readme.py::TestVolumeManagementSection::test_documents_nats_data_volume PASSED                           [ 51%]
tests/test_readme.py::TestVolumeManagementSection::test_documents_backup PASSED                                     [ 51%]
tests/test_readme.py::TestVolumeManagementSection::test_documents_restore PASSED                                    [ 51%]
tests/test_readme.py::TestVolumeManagementSection::test_documents_reset PASSED                                      [ 52%]
tests/test_readme.py::TestVolumeManagementSection::test_backup_includes_tar_command PASSED                          [ 52%]
tests/test_readme.py::TestVolumeManagementSection::test_restore_includes_tar_command PASSED                         [ 52%]
tests/test_readme.py::TestVolumeManagementSection::test_documents_stopping_without_data_loss PASSED                 [ 52%]
tests/test_readme.py::TestHealthCheckVerification::test_has_health_check_section PASSED                             [ 52%]
tests/test_readme.py::TestHealthCheckVerification::test_documents_healthz_endpoint PASSED                           [ 52%]
tests/test_readme.py::TestHealthCheckVerification::test_documents_curl_healthz PASSED                               [ 52%]
tests/test_readme.py::TestHealthCheckVerification::test_documents_jsz_endpoint PASSED                               [ 53%]
tests/test_readme.py::TestHealthCheckVerification::test_documents_varz_endpoint PASSED                              [ 53%]
tests/test_readme.py::TestHealthCheckVerification::test_documents_docker_compose_ps PASSED                          [ 53%]
tests/test_readme.py::TestHealthCheckVerification::test_documents_health_check_config PASSED                        [ 53%]
tests/test_readme.py::TestHealthCheckVerification::test_documents_verify_nats_script PASSED                         [ 53%]
tests/test_readme.py::TestDataLossWarning::test_has_warning_keyword PASSED                                          [ 53%]
tests/test_readme.py::TestDataLossWarning::test_warns_about_down_v PASSED                                           [ 53%]
tests/test_readme.py::TestDataLossWarning::test_warns_about_data_destruction PASSED                                 [ 54%]
tests/test_readme.py::TestDataLossWarning::test_warns_about_irreversibility PASSED                                  [ 54%]
tests/test_readme.py::TestDataLossWarning::test_warns_about_jetstream_data PASSED                                   [ 54%]
tests/test_readme.py::TestDockerfileBuildContext::test_has_dockerfile_section PASSED                                [ 54%]
tests/test_readme.py::TestDockerfileBuildContext::test_documents_build_context PASSED                               [ 54%]
tests/test_readme.py::TestDockerfileBuildContext::test_documents_base_image PASSED                                  [ 54%]
tests/test_readme.py::TestDockerfileBuildContext::test_documents_envsubst PASSED                                    [ 54%]
tests/test_readme.py::TestDockerfileBuildContext::test_documents_entrypoint PASSED                                  [ 55%]
tests/test_readme.py::TestDockerfileBuildContext::test_documents_gettext_package PASSED                             [ 55%]
tests/test_readme.py::TestDockerfileBuildContext::test_documents_dockerignore PASSED                                [ 55%]
tests/test_readme.py::TestDockerfileBuildContext::test_documents_password_injection_flow PASSED                     [ 55%]
tests/test_readme_streams.py::TestJetStreamStreamsSection::test_has_jetstream_streams_section PASSED                [ 55%]
tests/test_readme_streams.py::TestJetStreamStreamsSection::test_jetstream_streams_section_has_content PASSED        [ 55%]
tests/test_readme_streams.py::TestJetStreamStreamsSection::test_references_stream_definitions_file PASSED           [ 55%]
tests/test_readme_streams.py::TestCoreStreamsListed::test_core_stream_is_listed[PIPELINE] PASSED                    [ 56%]
tests/test_readme_streams.py::TestCoreStreamsListed::test_core_stream_is_listed[AGENTS] PASSED                      [ 56%]
tests/test_readme_streams.py::TestCoreStreamsListed::test_core_stream_is_listed[JARVIS] PASSED                      [ 56%]
tests/test_readme_streams.py::TestCoreStreamsListed::test_core_stream_is_listed[NOTIFICATIONS] PASSED               [ 56%]
tests/test_readme_streams.py::TestCoreStreamsListed::test_core_stream_is_listed[SYSTEM] PASSED                      [ 56%]
tests/test_readme_streams.py::TestCoreStreamsListed::test_core_stream_is_listed[FLEET] PASSED                       [ 56%]
tests/test_readme_streams.py::TestCoreStreamsListed::test_core_stream_has_description[PIPELINE] PASSED              [ 56%]
tests/test_readme_streams.py::TestCoreStreamsListed::test_core_stream_has_description[AGENTS] PASSED                [ 57%]
tests/test_readme_streams.py::TestCoreStreamsListed::test_core_stream_has_description[JARVIS] PASSED                [ 57%]
tests/test_readme_streams.py::TestCoreStreamsListed::test_core_stream_has_description[NOTIFICATIONS] PASSED         [ 57%]
tests/test_readme_streams.py::TestCoreStreamsListed::test_core_stream_has_description[SYSTEM] PASSED                [ 57%]
tests/test_readme_streams.py::TestCoreStreamsListed::test_core_stream_has_description[FLEET] PASSED                 [ 57%]
tests/test_readme_streams.py::TestCoreStreamsListed::test_all_six_core_streams_present PASSED                       [ 57%]
tests/test_readme_streams.py::TestCoreStreamsListed::test_core_streams_table_has_retention_column PASSED            [ 58%]
tests/test_readme_streams.py::TestCoreStreamsListed::test_core_streams_table_has_max_age_column PASSED              [ 58%]
tests/test_readme_streams.py::TestCoreStreamsListed::test_core_streams_section_heading PASSED                       [ 58%]
tests/test_readme_streams.py::TestProvisioningCommandsDocumented::test_has_provisioning_section PASSED              [ 58%]
tests/test_readme_streams.py::TestProvisioningCommandsDocumented::test_documents_provision_streams_script PASSED    [ 58%]
tests/test_readme_streams.py::TestProvisioningCommandsDocumented::test_documents_dry_run_flag PASSED                [ 58%]
tests/test_readme_streams.py::TestProvisioningCommandsDocumented::test_documents_nats_url_env PASSED                [ 58%]
tests/test_readme_streams.py::TestProvisioningCommandsDocumented::test_documents_nats_creds_env PASSED              [ 59%]
tests/test_readme_streams.py::TestProvisioningCommandsDocumented::test_documents_prerequisites PASSED               [ 59%]
tests/test_readme_streams.py::TestIdempotencyGuaranteesExplained::test_has_idempotency_section PASSED               [ 59%]
tests/test_readme_streams.py::TestIdempotencyGuaranteesExplained::test_explains_idempotent_pattern PASSED           [ 59%]
tests/test_readme_streams.py::TestIdempotencyGuaranteesExplained::test_explains_create_behaviour PASSED             [ 59%]
tests/test_readme_streams.py::TestIdempotencyGuaranteesExplained::test_explains_ok_behaviour PASSED                 [ 59%]
tests/test_readme_streams.py::TestIdempotencyGuaranteesExplained::test_explains_update_behaviour PASSED             [ 59%]
tests/test_readme_streams.py::TestIdempotencyGuaranteesExplained::test_explains_error_behaviour PASSED              [ 60%]
tests/test_readme_streams.py::TestIdempotencyGuaranteesExplained::test_explains_check_then_create_or_update PASSED  [ 60%]
tests/test_readme_streams.py::TestIdempotencyGuaranteesExplained::test_explains_safe_to_rerun PASSED                [ 60%]
tests/test_readme_streams.py::TestIdempotencyGuaranteesExplained::test_explains_summary_output PASSED               [ 60%]
tests/test_readme_streams.py::TestProjectStreamAdditionProcess::test_has_adding_stream_section PASSED               [ 60%]
tests/test_readme_streams.py::TestProjectStreamAdditionProcess::test_documents_json_definition_step PASSED          [ 60%]
tests/test_readme_streams.py::TestProjectStreamAdditionProcess::test_documents_account_permissions_step PASSED      [ 60%]
tests/test_readme_streams.py::TestProjectStreamAdditionProcess::test_documents_provision_step PASSED                [ 61%]
tests/test_readme_streams.py::TestProjectStreamAdditionProcess::test_documents_test_update_step PASSED              [ 61%]
tests/test_readme_streams.py::TestProjectStreamAdditionProcess::test_shows_json_example PASSED                      [ 61%]
tests/test_readme_streams.py::TestProjectStreamAdditionProcess::test_documents_project_scope PASSED                 [ 61%]
tests/test_readme_streams.py::TestProjectStreamAdditionProcess::test_has_project_streams_subsection PASSED          [ 61%]
tests/test_readme_streams.py::TestProjectStreamAdditionProcess::test_finproxy_project_stream_listed PASSED          [ 61%]
tests/test_readme_streams.py::TestKVBucketsDocumented::test_has_kv_buckets_subsection PASSED                        [ 61%]
tests/test_readme_streams.py::TestKVBucketsDocumented::test_kv_bucket_is_listed[agent-status] PASSED                [ 62%]
tests/test_readme_streams.py::TestKVBucketsDocumented::test_kv_bucket_is_listed[agent-registry] PASSED              [ 62%]
tests/test_readme_streams.py::TestKVBucketsDocumented::test_kv_bucket_is_listed[pipeline-state] PASSED              [ 62%]
tests/test_readme_streams.py::TestKVBucketsDocumented::test_kv_bucket_is_listed[jarvis-session] PASSED              [ 62%]
tests/test_readme_streams.py::TestKVBucketsDocumented::test_kv_bucket_table_has_ttl_column PASSED                   [ 62%]
tests/test_readme_streams.py::TestKVBucketsDocumented::test_documents_persistent_vs_expiring PASSED                 [ 62%]
tests/test_readme_streams.py::TestKVBucketsDocumented::test_kv_buckets_provisioned_alongside_streams PASSED         [ 62%]
tests/test_setup_gb10_script.py::TestSetupGb10ScriptExists::test_script_file_exists PASSED                          [ 63%]
tests/test_setup_gb10_script.py::TestSetupGb10ScriptExists::test_script_is_executable PASSED                        [ 63%]
tests/test_setup_gb10_script.py::TestSetupGb10ScriptExists::test_script_has_shebang PASSED                          [ 63%]
tests/test_setup_gb10_script.py::TestSetupGb10ScriptExists::test_script_is_not_empty PASSED                         [ 63%]
tests/test_setup_gb10_script.py::TestSetupGb10ScriptExists::test_uses_strict_error_handling PASSED                  [ 63%]
tests/test_setup_gb10_script.py::TestCallsKvProvisioning::test_calls_provision_kv PASSED                            [ 63%]
tests/test_setup_gb10_script.py::TestCallsKvProvisioning::test_calls_provision_streams PASSED                       [ 63%]
tests/test_setup_gb10_script.py::TestCallsKvProvisioning::test_kv_provisioning_after_stream_provisioning PASSED     [ 64%]
tests/test_setup_gb10_script.py::TestCallsKvProvisioning::test_kv_provisioning_before_verify PASSED                 [ 64%]
tests/test_setup_gb10_script.py::TestCallsKvProvisioning::test_stream_provisioning_before_verify PASSED             [ 64%]
tests/test_setup_gb10_script.py::TestKvProvisioningAfterHealth::test_has_health_wait PASSED                         [ 64%]
tests/test_setup_gb10_script.py::TestKvProvisioningAfterHealth::test_health_check_before_kv_provisioning PASSED     [ 64%]
tests/test_setup_gb10_script.py::TestKvProvisioningAfterHealth::test_health_check_before_stream_provisioning PASSED [ 64%]
tests/test_setup_gb10_script.py::TestKvProvisioningAfterHealth::test_has_health_timeout PASSED                      [ 64%]
tests/test_setup_gb10_script.py::TestKvProvisioningAfterHealth::test_exits_on_health_timeout PASSED                 [ 65%]
tests/test_setup_gb10_script.py::TestKvProvisioningAfterHealth::test_health_endpoint_check PASSED                   [ 65%]
tests/test_setup_gb10_script.py::TestExitOnKvFailure::test_checks_kv_provisioning_exit_code PASSED                  [ 65%]
tests/test_setup_gb10_script.py::TestExitOnKvFailure::test_exits_nonzero_on_kv_failure PASSED                       [ 65%]
tests/test_setup_gb10_script.py::TestExitOnKvFailure::test_error_message_on_kv_failure PASSED                       [ 65%]
tests/test_setup_gb10_script.py::TestExitOnKvFailure::test_kv_script_missing_exits_nonzero PASSED                   [ 65%]
tests/test_setup_gb10_script.py::TestKvVerification::test_runs_nats_kv_ls PASSED                                    [ 65%]
tests/test_setup_gb10_script.py::TestKvVerification::test_kv_ls_after_provisioning PASSED                           [ 66%]
tests/test_setup_gb10_script.py::TestKvVerification::test_kv_ls_in_verification_step PASSED                         [ 66%]
tests/test_setup_gb10_script.py::TestShellcheck::test_script_passes_shellcheck SKIPPED (shellcheck not installe...) [ 66%]
tests/test_setup_gb10_script.py::TestShellcheck::test_script_passes_shellcheck_warnings SKIPPED (shellcheck not...) [ 66%]
tests/test_setup_gb10_script.py::TestSetupSequenceOrder::test_has_eight_steps PASSED                                [ 66%]
tests/test_setup_gb10_script.py::TestSetupSequenceOrder::test_prerequisites_step PASSED                             [ 66%]
tests/test_setup_gb10_script.py::TestSetupSequenceOrder::test_docker_compose_step PASSED                            [ 66%]
tests/test_setup_gb10_script.py::TestSetupSequenceOrder::test_health_wait_step PASSED                               [ 67%]
tests/test_setup_gb10_script.py::TestSetupSequenceOrder::test_stream_provisioning_step PASSED                       [ 67%]
tests/test_setup_gb10_script.py::TestSetupSequenceOrder::test_kv_provisioning_step PASSED                           [ 67%]
tests/test_setup_gb10_script.py::TestSetupSequenceOrder::test_verify_step PASSED                                    [ 67%]
tests/test_setup_gb10_script.py::TestSetupSequenceOrder::test_docker_up_before_health_check PASSED                  [ 67%]
tests/test_setup_gb10_script.py::TestSetupGb10PrerequisiteChecks::test_checks_docker PASSED                         [ 67%]
tests/test_setup_gb10_script.py::TestSetupGb10PrerequisiteChecks::test_checks_docker_compose PASSED                 [ 67%]
tests/test_setup_gb10_script.py::TestSetupGb10PrerequisiteChecks::test_checks_curl PASSED                           [ 68%]
tests/test_setup_gb10_script.py::TestNatsCliInstallation::test_checks_nats_cli_installed PASSED                     [ 68%]
tests/test_setup_gb10_script.py::TestNatsCliInstallation::test_installs_nats_cli_if_missing PASSED                  [ 68%]
tests/test_setup_gb10_script.py::TestDockerComposeManagement::test_runs_docker_compose_up PASSED                    [ 68%]
tests/test_setup_gb10_script.py::TestDockerComposeManagement::test_uses_build_flag PASSED                           [ 68%]
tests/test_setup_gb10_script.py::TestDockerComposeManagement::test_uses_detach_flag PASSED                          [ 68%]
tests/test_setup_gb10_script.py::TestDockerComposeManagement::test_idempotent_container_check PASSED                [ 68%]
tests/test_setup_gb10_script.py::TestProvisionGating::test_kv_gated_on_nats_cli PASSED                              [ 69%]
tests/test_setup_gb10_script.py::TestProvisionGating::test_kv_gated_on_jq PASSED                                    [ 69%]
tests/test_setup_gb10_script.py::TestEnvironmentVariables::test_supports_nats_url PASSED                            [ 69%]
tests/test_setup_gb10_script.py::TestEnvironmentVariables::test_supports_nats_monitor_url PASSED                    [ 69%]
tests/test_setup_gb10_script.py::TestEnvironmentVariables::test_nats_url_default PASSED                             [ 69%]
tests/test_setup_script.py::TestSetupScriptExists::test_script_file_exists PASSED                                   [ 69%]
tests/test_setup_script.py::TestSetupScriptExists::test_script_is_executable PASSED                                 [ 69%]
tests/test_setup_script.py::TestSetupScriptExists::test_script_has_shebang PASSED                                   [ 70%]
tests/test_setup_script.py::TestSetupScriptExists::test_script_is_not_empty PASSED                                  [ 70%]
tests/test_setup_script.py::TestSetupScriptExists::test_uses_strict_error_handling PASSED                           [ 70%]
tests/test_setup_script.py::TestProvisionStreamsIntegration::test_calls_provision_streams PASSED                    [ 70%]
tests/test_setup_script.py::TestProvisionStreamsIntegration::test_provision_after_docker_compose_up PASSED          [ 70%]
tests/test_setup_script.py::TestProvisionStreamsIntegration::test_provision_before_verify PASSED                    [ 70%]
tests/test_setup_script.py::TestProvisionStreamsIntegration::test_provision_is_step_4 PASSED                        [ 70%]
tests/test_setup_script.py::TestProvisionStreamsIntegration::test_has_five_steps PASSED                             [ 71%]
tests/test_setup_script.py::TestSetupSequenceOrder::test_step_1_is_prerequisites PASSED                             [ 71%]
tests/test_setup_script.py::TestSetupSequenceOrder::test_step_2_is_env_file PASSED                                  [ 71%]
tests/test_setup_script.py::TestSetupSequenceOrder::test_step_3_is_docker_compose PASSED                            [ 71%]
tests/test_setup_script.py::TestSetupSequenceOrder::test_step_4_is_stream_provisioning PASSED                       [ 71%]
tests/test_setup_script.py::TestSetupSequenceOrder::test_step_5_is_verification PASSED                              [ 71%]
tests/test_setup_script.py::TestSetupPrerequisiteChecks::test_checks_docker PASSED                                  [ 72%]
tests/test_setup_script.py::TestSetupPrerequisiteChecks::test_checks_docker_compose PASSED                          [ 72%]
tests/test_setup_script.py::TestSetupProvisionGating::test_gates_on_nats_cli PASSED                                 [ 72%]
tests/test_setup_script.py::TestSetupProvisionGating::test_gates_on_jq PASSED                                       [ 72%]
tests/test_setup_script.py::TestSetupProvisionGating::test_skip_message_when_tools_missing PASSED                   [ 72%]
tests/test_setup_script.py::TestSetupCallsVerify::test_calls_verify_nats PASSED                                     [ 72%]
tests/test_setup_script.py::TestSetupCallsVerify::test_verify_after_provision PASSED                                [ 72%]
tests/test_setup_script.py::TestSetupDockerCompose::test_runs_docker_compose_up PASSED                              [ 73%]
tests/test_setup_script.py::TestSetupDockerCompose::test_uses_build_flag PASSED                                     [ 73%]
tests/test_setup_script.py::TestSetupDockerCompose::test_uses_detach_flag PASSED                                    [ 73%]
tests/test_setup_script.py::TestSetupDockerCompose::test_waits_for_healthy PASSED                                   [ 73%]
tests/test_stream_definitions.py::TestStreamDefsFileExists::test_file_exists PASSED                                 [ 73%]
tests/test_stream_definitions.py::TestStreamDefsFileExists::test_file_is_not_empty PASSED                           [ 73%]
tests/test_stream_definitions.py::TestStreamDefsFileExists::test_file_in_streams_directory PASSED                   [ 73%]
tests/test_stream_definitions.py::TestJsonValidity::test_json_is_parseable PASSED                                   [ 74%]
tests/test_stream_definitions.py::TestJsonValidity::test_has_streams_key PASSED                                     [ 74%]
tests/test_stream_definitions.py::TestJsonValidity::test_streams_is_array PASSED                                    [ 74%]
tests/test_stream_definitions.py::TestRequiredFields::test_all_streams_have_required_fields PASSED                  [ 74%]
tests/test_stream_definitions.py::TestRequiredFields::test_subjects_is_list_of_strings PASSED                       [ 74%]
tests/test_stream_definitions.py::TestRequiredFields::test_max_msgs_is_integer PASSED                               [ 74%]
tests/test_stream_definitions.py::TestRequiredFields::test_replicas_is_integer PASSED                               [ 74%]
tests/test_stream_definitions.py::TestRequiredFields::test_max_age_is_string PASSED                                 [ 75%]
tests/test_stream_definitions.py::TestRequiredFields::test_storage_is_string PASSED                                 [ 75%]
tests/test_stream_definitions.py::TestRetentionValues::test_all_retentions_are_valid PASSED                         [ 75%]
tests/test_stream_definitions.py::TestCoreStreams::test_all_six_core_streams_present PASSED                         [ 75%]
tests/test_stream_definitions.py::TestCoreStreams::test_core_streams_have_core_scope PASSED                         [ 75%]
tests/test_stream_definitions.py::TestCoreStreams::test_core_stream_subjects[PIPELINE] PASSED                       [ 75%]
tests/test_stream_definitions.py::TestCoreStreams::test_core_stream_subjects[AGENTS] PASSED                         [ 75%]
tests/test_stream_definitions.py::TestCoreStreams::test_core_stream_subjects[JARVIS] PASSED                         [ 76%]
tests/test_stream_definitions.py::TestCoreStreams::test_core_stream_subjects[NOTIFICATIONS] PASSED                  [ 76%]
tests/test_stream_definitions.py::TestCoreStreams::test_core_stream_subjects[SYSTEM] PASSED                         [ 76%]
tests/test_stream_definitions.py::TestCoreStreams::test_core_stream_subjects[FLEET] PASSED                          [ 76%]
tests/test_stream_definitions.py::TestCoreStreams::test_core_stream_retention[PIPELINE] PASSED                      [ 76%]
tests/test_stream_definitions.py::TestCoreStreams::test_core_stream_retention[AGENTS] PASSED                        [ 76%]
tests/test_stream_definitions.py::TestCoreStreams::test_core_stream_retention[JARVIS] PASSED                        [ 76%]
tests/test_stream_definitions.py::TestCoreStreams::test_core_stream_retention[NOTIFICATIONS] PASSED                 [ 77%]
tests/test_stream_definitions.py::TestCoreStreams::test_core_stream_retention[SYSTEM] PASSED                        [ 77%]
tests/test_stream_definitions.py::TestCoreStreams::test_core_stream_retention[FLEET] PASSED                         [ 77%]
tests/test_stream_definitions.py::TestCoreStreams::test_core_stream_max_age[PIPELINE] PASSED                        [ 77%]
tests/test_stream_definitions.py::TestCoreStreams::test_core_stream_max_age[AGENTS] PASSED                          [ 77%]
tests/test_stream_definitions.py::TestCoreStreams::test_core_stream_max_age[JARVIS] PASSED                          [ 77%]
tests/test_stream_definitions.py::TestCoreStreams::test_core_stream_max_age[NOTIFICATIONS] PASSED                   [ 77%]
tests/test_stream_definitions.py::TestCoreStreams::test_core_stream_max_age[SYSTEM] PASSED                          [ 78%]
tests/test_stream_definitions.py::TestCoreStreams::test_core_stream_max_age[FLEET] PASSED                           [ 78%]
tests/test_stream_definitions.py::TestCoreStreams::test_core_stream_max_msgs[PIPELINE] PASSED                       [ 78%]
tests/test_stream_definitions.py::TestCoreStreams::test_core_stream_max_msgs[AGENTS] PASSED                         [ 78%]
tests/test_stream_definitions.py::TestCoreStreams::test_core_stream_max_msgs[JARVIS] PASSED                         [ 78%]
tests/test_stream_definitions.py::TestCoreStreams::test_core_stream_max_msgs[NOTIFICATIONS] PASSED                  [ 78%]
tests/test_stream_definitions.py::TestCoreStreams::test_core_stream_max_msgs[SYSTEM] PASSED                         [ 78%]
tests/test_stream_definitions.py::TestCoreStreams::test_core_stream_max_msgs[FLEET] PASSED                          [ 79%]
tests/test_stream_definitions.py::TestCoreStreams::test_core_stream_storage[PIPELINE] PASSED                        [ 79%]
tests/test_stream_definitions.py::TestCoreStreams::test_core_stream_storage[AGENTS] PASSED                          [ 79%]
tests/test_stream_definitions.py::TestCoreStreams::test_core_stream_storage[JARVIS] PASSED                          [ 79%]
tests/test_stream_definitions.py::TestCoreStreams::test_core_stream_storage[NOTIFICATIONS] PASSED                   [ 79%]
tests/test_stream_definitions.py::TestCoreStreams::test_core_stream_storage[SYSTEM] PASSED                          [ 79%]
tests/test_stream_definitions.py::TestCoreStreams::test_core_stream_storage[FLEET] PASSED                           [ 79%]
tests/test_stream_definitions.py::TestCoreStreams::test_core_stream_replicas[PIPELINE] PASSED                       [ 80%]
tests/test_stream_definitions.py::TestCoreStreams::test_core_stream_replicas[AGENTS] PASSED                         [ 80%]
tests/test_stream_definitions.py::TestCoreStreams::test_core_stream_replicas[JARVIS] PASSED                         [ 80%]
tests/test_stream_definitions.py::TestCoreStreams::test_core_stream_replicas[NOTIFICATIONS] PASSED                  [ 80%]
tests/test_stream_definitions.py::TestCoreStreams::test_core_stream_replicas[SYSTEM] PASSED                         [ 80%]
tests/test_stream_definitions.py::TestCoreStreams::test_core_stream_replicas[FLEET] PASSED                          [ 80%]
tests/test_stream_definitions.py::TestFinproxyStream::test_finproxy_stream_exists PASSED                            [ 80%]
tests/test_stream_definitions.py::TestFinproxyStream::test_finproxy_scope_is_project PASSED                         [ 81%]
tests/test_stream_definitions.py::TestFinproxyStream::test_finproxy_subjects PASSED                                 [ 81%]
tests/test_stream_definitions.py::TestFinproxyStream::test_finproxy_retention_is_work PASSED                        [ 81%]
tests/test_stream_definitions.py::TestFinproxyStream::test_finproxy_max_age_is_24h PASSED                           [ 81%]
tests/test_stream_definitions.py::TestFinproxyStream::test_finproxy_max_msgs_is_5000 PASSED                         [ 81%]
tests/test_stream_definitions.py::TestFinproxyStream::test_finproxy_storage_is_file PASSED                          [ 81%]
tests/test_stream_definitions.py::TestFinproxyStream::test_finproxy_replicas_is_1 PASSED                            [ 81%]
tests/test_stream_definitions.py::TestNatsDurationFormat::test_max_age_uses_valid_nats_duration PASSED              [ 82%]
tests/test_stream_definitions.py::TestNatsDurationFormat::test_specific_stream_max_age_format[PIPELINE-7d] PASSED   [ 82%]
tests/test_stream_definitions.py::TestNatsDurationFormat::test_specific_stream_max_age_format[AGENTS-24h] PASSED    [ 82%]
tests/test_stream_definitions.py::TestNatsDurationFormat::test_specific_stream_max_age_format[JARVIS-1h] PASSED     [ 82%]
tests/test_stream_definitions.py::TestNatsDurationFormat::test_specific_stream_max_age_format[NOTIFICATIONS-24h] PASSED [ 82%]
tests/test_stream_definitions.py::TestNatsDurationFormat::test_specific_stream_max_age_format[SYSTEM-1h] PASSED     [ 82%]
tests/test_stream_definitions.py::TestNatsDurationFormat::test_specific_stream_max_age_format[FLEET-1h] PASSED      [ 82%]
tests/test_stream_definitions.py::TestNatsDurationFormat::test_specific_stream_max_age_format[FINPROXY-24h] PASSED  [ 83%]
tests/test_stream_definitions.py::TestSubjectNaming::test_subjects_follow_dot_separated_hierarchical_naming PASSED  [ 83%]
tests/test_stream_definitions.py::TestSubjectNaming::test_subjects_use_wildcard_suffix PASSED                       [ 83%]
tests/test_stream_definitions.py::TestSpecCompliance::test_pipeline_retention_is_work PASSED                        [ 83%]
tests/test_stream_definitions.py::TestSpecCompliance::test_agents_max_age_is_24h PASSED                             [ 83%]
tests/test_stream_definitions.py::TestSpecCompliance::test_jarvis_max_msgs_is_1000 PASSED                           [ 83%]
tests/test_stream_definitions.py::TestSpecCompliance::test_all_streams_replicas_is_1 PASSED                         [ 83%]
tests/test_stream_definitions.py::TestSpecCompliance::test_all_streams_storage_is_file PASSED                       [ 84%]
tests/test_stream_definitions.py::TestStreamCount::test_total_stream_count PASSED                                   [ 84%]
tests/test_stream_definitions.py::TestStreamCount::test_no_duplicate_stream_names PASSED                            [ 84%]
tests/test_stream_definitions.py::TestStreamCount::test_no_duplicate_subjects PASSED                                [ 84%]
tests/test_stream_definitions.py::TestKvBucketsExist::test_kv_buckets_key_exists PASSED                             [ 84%]
tests/test_stream_definitions.py::TestKvBucketsExist::test_kv_buckets_is_array PASSED                               [ 84%]
tests/test_stream_definitions.py::TestKvBucketsExist::test_exactly_4_kv_buckets PASSED                              [ 84%]
tests/test_stream_definitions.py::TestKvBucketsExist::test_all_expected_buckets_present PASSED                      [ 85%]
tests/test_stream_definitions.py::TestKvBucketsExist::test_no_duplicate_bucket_names PASSED                         [ 85%]
tests/test_stream_definitions.py::TestKvBucketRequiredFields::test_all_buckets_have_required_fields PASSED          [ 85%]
tests/test_stream_definitions.py::TestKvBucketRequiredFields::test_name_is_string PASSED                            [ 85%]
tests/test_stream_definitions.py::TestKvBucketRequiredFields::test_description_is_string PASSED                     [ 85%]
tests/test_stream_definitions.py::TestKvBucketRequiredFields::test_description_is_not_empty PASSED                  [ 85%]
tests/test_stream_definitions.py::TestKvBucketTtlValues::test_ttl_is_null_or_valid_duration PASSED                  [ 86%]
tests/test_stream_definitions.py::TestKvBucketTtlValues::test_expected_ttl_values[agent-status] PASSED              [ 86%]
tests/test_stream_definitions.py::TestKvBucketTtlValues::test_expected_ttl_values[agent-registry] PASSED            [ 86%]
tests/test_stream_definitions.py::TestKvBucketTtlValues::test_expected_ttl_values[pipeline-state] PASSED            [ 86%]
tests/test_stream_definitions.py::TestKvBucketTtlValues::test_expected_ttl_values[jarvis-session] PASSED            [ 86%]
tests/test_stream_definitions.py::TestKvBucketTtlValues::test_agent_status_is_persistent PASSED                     [ 86%]
tests/test_stream_definitions.py::TestKvBucketTtlValues::test_agent_registry_is_persistent PASSED                   [ 86%]
tests/test_stream_definitions.py::TestKvBucketTtlValues::test_pipeline_state_ttl_is_7d PASSED                       [ 87%]
tests/test_stream_definitions.py::TestKvBucketTtlValues::test_jarvis_session_ttl_is_1h PASSED                       [ 87%]
tests/test_stream_definitions.py::TestKvBucketNaming::test_bucket_names_are_kebab_case PASSED                       [ 87%]
tests/test_stream_definitions.py::TestKvBucketsContract::test_top_level_kv_buckets_key_exists PASSED                [ 87%]
tests/test_stream_definitions.py::TestKvBucketsContract::test_at_least_4_kv_buckets PASSED                          [ 87%]
tests/test_stream_definitions.py::TestKvBucketsContract::test_all_buckets_have_required_fields PASSED               [ 87%]
tests/test_verify_nats_script.py::TestScriptExists::test_script_file_exists PASSED                                  [ 87%]
tests/test_verify_nats_script.py::TestScriptExists::test_script_is_executable PASSED                                [ 88%]
tests/test_verify_nats_script.py::TestScriptExists::test_script_has_shebang PASSED                                  [ 88%]
tests/test_verify_nats_script.py::TestScriptExists::test_script_is_not_empty PASSED                                 [ 88%]
tests/test_verify_nats_script.py::TestHealthCheck::test_checks_healthz_endpoint PASSED                              [ 88%]
tests/test_verify_nats_script.py::TestHealthCheck::test_uses_curl_for_healthcheck PASSED                            [ 88%]
tests/test_verify_nats_script.py::TestJetStreamVerification::test_checks_jsz_endpoint PASSED                        [ 88%]
tests/test_verify_nats_script.py::TestJetStreamVerification::test_uses_curl_for_jetstream PASSED                    [ 88%]
tests/test_verify_nats_script.py::TestJetStreamVerification::test_validates_jetstream_info PASSED                   [ 89%]
tests/test_verify_nats_script.py::TestServerNameVerification::test_checks_varz_endpoint PASSED                      [ 89%]
tests/test_verify_nats_script.py::TestServerNameVerification::test_uses_curl_for_server_info PASSED                 [ 89%]
tests/test_verify_nats_script.py::TestServerNameVerification::test_checks_server_name_ships_computer PASSED         [ 89%]
tests/test_verify_nats_script.py::TestServerNameVerification::test_checks_server_name_field PASSED                  [ 89%]
tests/test_verify_nats_script.py::TestPassFailReporting::test_reports_pass PASSED                                   [ 89%]
tests/test_verify_nats_script.py::TestPassFailReporting::test_reports_fail PASSED                                   [ 89%]
tests/test_verify_nats_script.py::TestPassFailReporting::test_pass_and_fail_used_in_output PASSED                   [ 90%]
tests/test_verify_nats_script.py::TestPassFailReporting::test_reports_multiple_checks PASSED                        [ 90%]
tests/test_verify_nats_script.py::TestExitCode::test_has_exit_with_non_zero PASSED                                  [ 90%]
tests/test_verify_nats_script.py::TestExitCode::test_tracks_failure_state PASSED                                    [ 90%]
tests/test_verify_nats_script.py::TestExitCode::test_has_exit_zero_on_success PASSED                                [ 90%]
tests/test_verify_nats_script.py::TestCurlBasedNoNatsCLI::test_uses_curl_command PASSED                             [ 90%]
tests/test_verify_nats_script.py::TestCurlBasedNoNatsCLI::test_does_not_require_nats_cli PASSED                     [ 90%]
tests/test_verify_nats_script.py::TestCurlBasedNoNatsCLI::test_optional_nats_cli_for_auth PASSED                    [ 91%]
tests/test_verify_nats_script.py::TestTimeoutAndRobustness::test_has_timeout_mechanism PASSED                       [ 91%]
tests/test_verify_nats_script.py::TestTimeoutAndRobustness::test_has_set_options PASSED                             [ 91%]
tests/test_verify_nats_script.py::TestTimeoutAndRobustness::test_has_explanatory_comments PASSED                    [ 91%]
tests/test_verify_nats_script.py::TestTimeoutAndRobustness::test_uses_curl_silent_mode PASSED                       [ 91%]
tests/test_verify_nats_script.py::TestTimeoutAndRobustness::test_reports_version PASSED                             [ 91%]
tests/test_verify_streams.py::TestStreamVerificationSection::test_has_check_5_section PASSED                        [ 91%]
tests/test_verify_streams.py::TestStreamVerificationSection::test_has_jetstream_streams_header PASSED               [ 92%]
tests/test_verify_streams.py::TestStreamListOutput::test_uses_ok_status_marker PASSED                               [ 92%]
tests/test_verify_streams.py::TestStreamListOutput::test_uses_missing_status_marker PASSED                          [ 92%]
tests/test_verify_streams.py::TestStreamListOutput::test_ok_and_missing_in_echo PASSED                              [ 92%]
tests/test_verify_streams.py::TestStreamListOutput::test_ok_includes_stream_name PASSED                             [ 92%]
tests/test_verify_streams.py::TestStreamListOutput::test_missing_includes_stream_name PASSED                        [ 92%]
tests/test_verify_streams.py::TestExpectedStreamsCoverage::test_lists_pipeline_stream PASSED                        [ 92%]
tests/test_verify_streams.py::TestExpectedStreamsCoverage::test_lists_agents_stream PASSED                          [ 93%]
tests/test_verify_streams.py::TestExpectedStreamsCoverage::test_lists_jarvis_stream PASSED                          [ 93%]
tests/test_verify_streams.py::TestExpectedStreamsCoverage::test_lists_notifications_stream PASSED                   [ 93%]
tests/test_verify_streams.py::TestExpectedStreamsCoverage::test_lists_system_stream PASSED                          [ 93%]
tests/test_verify_streams.py::TestExpectedStreamsCoverage::test_lists_fleet_stream PASSED                           [ 93%]
tests/test_verify_streams.py::TestExpectedStreamsCoverage::test_lists_finproxy_stream PASSED                        [ 93%]
tests/test_verify_streams.py::TestExpectedStreamsCoverage::test_all_defined_streams_are_checked PASSED              [ 93%]
tests/test_verify_streams.py::TestExpectedStreamsCoverage::test_expected_streams_count_matches PASSED               [ 94%]
tests/test_verify_streams.py::TestStreamCheckMechanism::test_uses_nats_stream_info PASSED                           [ 94%]
tests/test_verify_streams.py::TestStreamCheckMechanism::test_iterates_over_expected_streams PASSED                  [ 94%]
tests/test_verify_streams.py::TestStreamCheckMechanism::test_reports_stream_counts PASSED                           [ 94%]
tests/test_verify_streams.py::TestNatsCliGating::test_check_5_gated_on_nats_cli PASSED                              [ 94%]
tests/test_verify_streams.py::TestNatsCliGating::test_graceful_skip_when_no_nats_cli PASSED                         [ 94%]
tests/test_verify_streams.py::TestNatsCliGating::test_skip_suggests_install PASSED                                  [ 94%]
tests/test_verify_streams.py::TestNatsCliGating::test_no_hard_failure_without_nats_cli PASSED                       [ 95%]
tests/test_verify_streams.py::TestStreamCheckDoesNotAffectExitCode::test_stream_check_does_not_fail_check PASSED    [ 95%]
tests/test_verify_streams.py::TestExistingChecksSurvive::test_check_1_health_still_present PASSED                   [ 95%]
tests/test_verify_streams.py::TestExistingChecksSurvive::test_check_2_jetstream_still_present PASSED                [ 95%]
tests/test_verify_streams.py::TestExistingChecksSurvive::test_check_3_server_info_still_present PASSED              [ 95%]
tests/test_verify_streams.py::TestExistingChecksSurvive::test_check_4_auth_still_present PASSED                     [ 95%]
tests/test_verify_streams.py::TestExistingChecksSurvive::test_summary_still_present PASSED                          [ 95%]
tests/test_verify_streams.py::TestExistingChecksSurvive::test_check_5_after_check_4 PASSED                          [ 96%]
tests/test_verify_streams.py::TestExistingChecksSurvive::test_check_5_before_summary PASSED                         [ 96%]
tests/test_verify_streams.py::TestProvisionHintForMissingStreams::test_suggests_provision_script PASSED             [ 96%]
tests/test_volume_persistence.py::TestStreamCreationConfig::test_jetstream_enabled_in_server_conf PASSED            [ 96%]
tests/test_volume_persistence.py::TestStreamCreationConfig::test_jetstream_store_dir_configured PASSED              [ 96%]
tests/test_volume_persistence.py::TestStreamCreationConfig::test_jetstream_has_file_storage_limits PASSED           [ 96%]
tests/test_volume_persistence.py::TestStreamCreationConfig::test_jetstream_has_memory_limits PASSED                 [ 96%]
tests/test_volume_persistence.py::TestStreamCreationConfig::test_volume_mounted_at_store_dir PASSED                 [ 97%]
tests/test_volume_persistence.py::TestStreamCreationConfig::test_client_port_exposed_for_publishing PASSED          [ 97%]
tests/test_volume_persistence.py::TestStreamSurvivesRestart::test_top_level_named_volume_defined PASSED             [ 97%]
tests/test_volume_persistence.py::TestStreamSurvivesRestart::test_named_volume_not_anonymous PASSED                 [ 97%]
tests/test_volume_persistence.py::TestStreamSurvivesRestart::test_store_dir_matches_volume_mount PASSED             [ 97%]
tests/test_volume_persistence.py::TestStreamSurvivesRestart::test_volume_is_not_tmpfs PASSED                        [ 97%]
tests/test_volume_persistence.py::TestMessageRetrievalAfterRestart::test_jetstream_file_storage_configured PASSED   [ 97%]
tests/test_volume_persistence.py::TestMessageRetrievalAfterRestart::test_store_dir_is_absolute_path PASSED          [ 98%]
tests/test_volume_persistence.py::TestMessageRetrievalAfterRestart::test_volume_mount_preserves_data_directory PASSED [ 98%]
tests/test_volume_persistence.py::TestMessageRetrievalAfterRestart::test_volume_not_read_only PASSED                [ 98%]
tests/test_volume_persistence.py::TestVolumeNaming::test_volume_name_is_nats_data PASSED                            [ 98%]
tests/test_volume_persistence.py::TestVolumeNaming::test_volume_uses_default_driver PASSED                          [ 98%]
tests/test_volume_persistence.py::TestVolumeNaming::test_volume_referenced_in_service PASSED                        [ 98%]
tests/test_volume_persistence.py::TestVolumeNaming::test_compose_project_name_derivation PASSED                     [ 98%]
tests/test_volume_persistence.py::TestDataLossWarning::test_compose_file_warns_about_down_v PASSED                  [ 99%]
tests/test_volume_persistence.py::TestDataLossWarning::test_readme_warns_about_data_loss PASSED                     [ 99%]
tests/test_volume_persistence.py::TestDataLossWarning::test_warning_mentions_jetstream_or_persistence PASSED        [ 99%]
tests/test_volume_persistence.py::TestVolumePersistenceIntegration::test_ac001_stream_creation_and_publish FAILED   [ 99%]
tests/test_volume_persistence.py::TestVolumePersistenceIntegration::test_ac002_stream_survives_restart FAILED       [ 99%]
tests/test_volume_persistence.py::TestVolumePersistenceIntegration::test_ac003_messages_retrievable_after_restart FAILED [ 99%]
tests/test_volume_persistence.py::TestVolumePersistenceIntegration::test_ac004_volume_listed_in_docker PASSED       [100%]

======================================================== FAILURES =========================================================
_________________________ TestVolumePersistenceIntegration.test_ac001_stream_creation_and_publish _________________________

self = <test_volume_persistence.TestVolumePersistenceIntegration object at 0xf97bf6a88a40>

    def test_ac001_stream_creation_and_publish(self) -> None:
        """AC-001: Create a JetStream stream and publish messages via nats CLI."""
        # Ensure container is up and healthy
        self._run("docker compose up -d")
        assert self._wait_for_healthy(), "NATS container did not become healthy"
    
        # Create a test stream
        result = self._run(
            "docker compose exec -T nats nats -s nats://localhost:4222 "
            "stream add PERSISTENCE_TEST "
            "--subjects='persistence.test' "
            "--storage=file "
            "--retention=limits "
            "--max-msgs=-1 "
            "--max-bytes=-1 "
            "--max-age=1h "
            "--max-msg-size=-1 "
            "--discard=old "
            "--replicas=1 "
            "--no-allow-rollup "
            "--deny-delete "
            "--deny-purge "
            "--defaults 2>/dev/null || true"
        )
    
        # Publish test messages
        for i in range(3):
            pub_result = self._run(
                f"docker compose exec -T nats nats -s nats://localhost:4222 "
                f"pub persistence.test 'test-message-{i}'"
            )
>           assert pub_result.returncode == 0, (
                f"Failed to publish message {i}: {pub_result.stderr}"
            )
E           AssertionError: Failed to publish message 0: 
E           assert 127 == 0
E            +  where 127 = CompletedProcess(args="docker compose exec -T nats nats -s nats://localhost:4222 pub persistence.test 'test-message-0'", returncode=127, stdout='OCI runtime exec failed: exec failed: unable to start container process: exec: "nats": executable file not found in $PATH\n', stderr='').returncode

tests/test_volume_persistence.py:447: AssertionError
___________________________ TestVolumePersistenceIntegration.test_ac002_stream_survives_restart ___________________________

self = <test_volume_persistence.TestVolumePersistenceIntegration object at 0xf97bf6a899d0>

    def test_ac002_stream_survives_restart(self) -> None:
        """AC-002: Stream persists after docker compose down + up."""
        # Start fresh and create stream
        self._run("docker compose up -d")
        assert self._wait_for_healthy(), "NATS container did not become healthy"
    
        # Create stream
        self._run(
            "docker compose exec -T nats nats -s nats://localhost:4222 "
            "stream add SURVIVAL_TEST "
            "--subjects='survival.test' "
            "--storage=file "
            "--retention=limits "
            "--max-msgs=-1 "
            "--max-bytes=-1 "
            "--max-age=1h "
            "--max-msg-size=-1 "
            "--discard=old "
            "--replicas=1 "
            "--defaults 2>/dev/null || true"
        )
    
        # Publish a message
        self._run(
            "docker compose exec -T nats nats -s nats://localhost:4222 "
            "pub survival.test 'before-restart'"
        )
    
        # docker compose down (preserves volumes) then up
        self._run("docker compose down")
        self._run("docker compose up -d")
        assert self._wait_for_healthy(max_wait=45), (
            "NATS container did not become healthy after restart"
        )
    
        # Verify stream still exists
        info_result = self._run(
            "docker compose exec -T nats nats -s nats://localhost:4222 "
            "stream info SURVIVAL_TEST --json"
        )
>       assert info_result.returncode == 0, (
            f"Stream SURVIVAL_TEST not found after restart: {info_result.stderr}"
        )
E       AssertionError: Stream SURVIVAL_TEST not found after restart: 
E       assert 127 == 0
E        +  where 127 = CompletedProcess(args='docker compose exec -T nats nats -s nats://localhost:4222 stream info SURVIVAL_TEST --json', returncode=127, stdout='OCI runtime exec failed: exec failed: unable to start container process: exec: "nats": executable file not found in $PATH\n', stderr='').returncode

tests/test_volume_persistence.py:501: AssertionError
_____________________ TestVolumePersistenceIntegration.test_ac003_messages_retrievable_after_restart ______________________

self = <test_volume_persistence.TestVolumePersistenceIntegration object at 0xf97bf6a89d00>

    def test_ac003_messages_retrievable_after_restart(self) -> None:
        """AC-003: Published messages are retrievable after docker compose down + up."""
        # Start and create stream with unique name
        self._run("docker compose up -d")
        assert self._wait_for_healthy(), "NATS container did not become healthy"
    
        # Create stream
        self._run(
            "docker compose exec -T nats nats -s nats://localhost:4222 "
            "stream add RETRIEVAL_TEST "
            "--subjects='retrieval.test' "
            "--storage=file "
            "--retention=limits "
            "--max-msgs=-1 "
            "--max-bytes=-1 "
            "--max-age=1h "
            "--max-msg-size=-1 "
            "--discard=old "
            "--replicas=1 "
            "--defaults 2>/dev/null || true"
        )
    
        # Publish messages
        for i in range(5):
            self._run(
                f"docker compose exec -T nats nats -s nats://localhost:4222 "
                f"pub retrieval.test 'persistent-msg-{i}'"
            )
    
        # Restart
        self._run("docker compose down")
        self._run("docker compose up -d")
        assert self._wait_for_healthy(max_wait=45), (
            "NATS container did not become healthy after restart"
        )
    
        # Retrieve messages — check stream info shows message count
        info_result = self._run(
            "docker compose exec -T nats nats -s nats://localhost:4222 "
            "stream info RETRIEVAL_TEST --json"
        )
>       assert info_result.returncode == 0, (
            f"Stream not found after restart: {info_result.stderr}"
        )
E       AssertionError: Stream not found after restart: 
E       assert 127 == 0
E        +  where 127 = CompletedProcess(args='docker compose exec -T nats nats -s nats://localhost:4222 stream info RETRIEVAL_TEST --json', returncode=127, stdout='OCI runtime exec failed: exec failed: unable to start container process: exec: "nats": executable file not found in $PATH\n', stderr='').returncode

tests/test_volume_persistence.py:549: AssertionError
==================================================== warnings summary =====================================================
tests/test_kv_definitions.py:480
  /home/richardwoollcott/Projects/appmilla_github/nats-infrastructure/tests/test_kv_definitions.py:480: PytestUnknownMarkWarning: Unknown pytest.mark.seam - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.seam

tests/test_kv_watch_integration.py:193
  /home/richardwoollcott/Projects/appmilla_github/nats-infrastructure/tests/test_kv_watch_integration.py:193: PytestUnknownMarkWarning: Unknown pytest.mark.integration - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.integration

tests/test_kv_watch_integration.py:259
  /home/richardwoollcott/Projects/appmilla_github/nats-infrastructure/tests/test_kv_watch_integration.py:259: PytestUnknownMarkWarning: Unknown pytest.mark.integration - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.integration

tests/test_kv_watch_integration.py:315
  /home/richardwoollcott/Projects/appmilla_github/nats-infrastructure/tests/test_kv_watch_integration.py:315: PytestUnknownMarkWarning: Unknown pytest.mark.integration - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.integration

tests/test_kv_watch_integration.py:409
  /home/richardwoollcott/Projects/appmilla_github/nats-infrastructure/tests/test_kv_watch_integration.py:409: PytestUnknownMarkWarning: Unknown pytest.mark.integration - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.integration

tests/test_kv_watch_integration.py:494
  /home/richardwoollcott/Projects/appmilla_github/nats-infrastructure/tests/test_kv_watch_integration.py:494: PytestUnknownMarkWarning: Unknown pytest.mark.integration - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.integration

tests/test_kv_watch_integration.py:588
  /home/richardwoollcott/Projects/appmilla_github/nats-infrastructure/tests/test_kv_watch_integration.py:588: PytestUnknownMarkWarning: Unknown pytest.mark.integration - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.integration

tests/test_kv_watch_integration.py:660
  /home/richardwoollcott/Projects/appmilla_github/nats-infrastructure/tests/test_kv_watch_integration.py:660: PytestUnknownMarkWarning: Unknown pytest.mark.integration - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.integration

tests/test_kv_watch_integration.py:738
  /home/richardwoollcott/Projects/appmilla_github/nats-infrastructure/tests/test_kv_watch_integration.py:738: PytestUnknownMarkWarning: Unknown pytest.mark.integration - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.integration

tests/test_provision_streams.py:460
  /home/richardwoollcott/Projects/appmilla_github/nats-infrastructure/tests/test_provision_streams.py:460: PytestUnknownMarkWarning: Unknown pytest.mark.seam - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.seam

tests/test_provision_streams.py:461
  /home/richardwoollcott/Projects/appmilla_github/nats-infrastructure/tests/test_provision_streams.py:461: PytestUnknownMarkWarning: Unknown pytest.mark.integration_contract - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.integration_contract("stream-definitions.json")

tests/test_stream_definitions.py:710
  /home/richardwoollcott/Projects/appmilla_github/nats-infrastructure/tests/test_stream_definitions.py:710: PytestUnknownMarkWarning: Unknown pytest.mark.seam - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.seam

tests/test_volume_persistence.py:372
  /home/richardwoollcott/Projects/appmilla_github/nats-infrastructure/tests/test_volume_persistence.py:372: PytestUnknownMarkWarning: Unknown pytest.mark.integration - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.integration

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================================================= short test summary info =================================================
FAILED tests/test_volume_persistence.py::TestVolumePersistenceIntegration::test_ac001_stream_creation_and_publish - AssertionError: Failed to publish message 0: 
FAILED tests/test_volume_persistence.py::TestVolumePersistenceIntegration::test_ac002_stream_survives_restart - AssertionError: Stream SURVIVAL_TEST not found after restart: 
FAILED tests/test_volume_persistence.py::TestVolumePersistenceIntegration::test_ac003_messages_retrievable_after_restart - AssertionError: Stream not found after restart: 
================================= 3 failed, 656 passed, 34 skipped, 13 warnings in 13.41s =================================
richardwoollcott@promaxgb10-41b1:~/Projects/appmilla_github/nats-infrastructure$ 
