richardwoollcott@promaxgb10-41b1:~/Projects/appmilla_github/nats-infrastructure$ pytest -m integration tests/test_volume_persistence.py -v
=================================================== test session starts ===================================================
platform linux -- Python 3.12.3, pytest-9.0.2, pluggy-1.6.0 -- /usr/bin/python3
cachedir: .pytest_cache
rootdir: /home/richardwoollcott/Projects/appmilla_github/nats-infrastructure
plugins: asyncio-1.3.0, anyio-4.12.1, cov-7.0.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 25 items / 21 deselected / 4 selected                                                                           

tests/test_volume_persistence.py::TestVolumePersistenceIntegration::test_ac001_stream_creation_and_publish FAILED   [ 25%]
tests/test_volume_persistence.py::TestVolumePersistenceIntegration::test_ac002_stream_survives_restart FAILED       [ 50%]
tests/test_volume_persistence.py::TestVolumePersistenceIntegration::test_ac003_messages_retrievable_after_restart FAILED [ 75%]
tests/test_volume_persistence.py::TestVolumePersistenceIntegration::test_ac004_volume_listed_in_docker PASSED       [100%]

======================================================== FAILURES =========================================================
_________________________ TestVolumePersistenceIntegration.test_ac001_stream_creation_and_publish _________________________

self = <test_volume_persistence.TestVolumePersistenceIntegration object at 0xfef9e5eec350>

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

self = <test_volume_persistence.TestVolumePersistenceIntegration object at 0xfef9e5eed8b0>

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

self = <test_volume_persistence.TestVolumePersistenceIntegration object at 0xfef9e5eedbb0>

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
tests/test_volume_persistence.py:372
  /home/richardwoollcott/Projects/appmilla_github/nats-infrastructure/tests/test_volume_persistence.py:372: PytestUnknownMarkWarning: Unknown pytest.mark.integration - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.integration

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================================================= short test summary info =================================================
FAILED tests/test_volume_persistence.py::TestVolumePersistenceIntegration::test_ac001_stream_creation_and_publish - AssertionError: Failed to publish message 0: 
FAILED tests/test_volume_persistence.py::TestVolumePersistenceIntegration::test_ac002_stream_survives_restart - AssertionError: Stream SURVIVAL_TEST not found after restart: 
FAILED tests/test_volume_persistence.py::TestVolumePersistenceIntegration::test_ac003_messages_retrievable_after_restart - AssertionError: Stream not found after restart: 
================================= 3 failed, 1 passed, 21 deselected, 1 warning in 12.99s ==================================
richardwoollcott@promaxgb10-41b1:~/Projects/appmilla_github/nats-infrastructure$ 
