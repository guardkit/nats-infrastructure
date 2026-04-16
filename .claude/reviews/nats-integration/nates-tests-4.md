richardwoollcott@promaxgb10-41b1:~/Projects/appmilla_github/nats-infrastructure$ source .env
richardwoollcott@promaxgb10-41b1:~/Projects/appmilla_github/nats-infrastructure$ pytest -m integration tests/test_volume_persistence.py -v
=================================================== test session starts ===================================================
platform linux -- Python 3.12.3, pytest-9.0.2, pluggy-1.6.0 -- /usr/bin/python3
cachedir: .pytest_cache
rootdir: /home/richardwoollcott/Projects/appmilla_github/nats-infrastructure
configfile: pyproject.toml
plugins: asyncio-1.3.0, anyio-4.12.1, cov-7.0.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 25 items / 21 deselected / 4 selected                                                                           

tests/test_volume_persistence.py::TestVolumePersistenceIntegration::test_ac001_stream_creation_and_publish FAILED   [ 25%]
tests/test_volume_persistence.py::TestVolumePersistenceIntegration::test_ac002_stream_survives_restart FAILED                      [ 50%]
tests/test_volume_persistence.py::TestVolumePersistenceIntegration::test_ac003_messages_retrievable_after_restart FAILED           [ 75%]
tests/test_volume_persistence.py::TestVolumePersistenceIntegration::test_ac004_volume_listed_in_docker PASSED                      [100%]

================================================================ FAILURES ================================================================
________________________________ TestVolumePersistenceIntegration.test_ac001_stream_creation_and_publish _________________________________

self = <test_volume_persistence.TestVolumePersistenceIntegration object at 0xf6fdfc84fbc0>

    def test_ac001_stream_creation_and_publish(self) -> None:
        """AC-001: Create a JetStream stream and publish messages via nats CLI."""
        # Ensure container is up and healthy
        self._run("docker compose up -d")
        assert self._wait_for_healthy(), "NATS container did not become healthy"
    
        # Create a test stream (nats CLI runs on host, connects to exposed port)
        result = self._run(
            self._nats_cmd(
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
        )
    
        # Publish test messages
        for i in range(3):
            pub_result = self._run(
                self._nats_cmd(f"pub persistence.test 'test-message-{i}'")
            )
>           assert pub_result.returncode == 0, (
                f"Failed to publish message {i}: {pub_result.stderr}"
            )
E           AssertionError: Failed to publish message 0: nats: error: nats: Authorization Violation
E             
E           assert 1 == 0
E            +  where 1 = CompletedProcess(args="nats -s nats://localhost:4222 --user rich --password '' pub persistence.test 'test-message-0'", returncode=1, stdout='', stderr='nats: error: nats: Authorization Violation\n').returncode

tests/test_volume_persistence.py:455: AssertionError
__________________________________ TestVolumePersistenceIntegration.test_ac002_stream_survives_restart ___________________________________

self = <test_volume_persistence.TestVolumePersistenceIntegration object at 0xf6fdfc84f5c0>

    def test_ac002_stream_survives_restart(self) -> None:
        """AC-002: Stream persists after docker compose down + up."""
        # Start fresh and create stream
        self._run("docker compose up -d")
        assert self._wait_for_healthy(), "NATS container did not become healthy"
    
        # Create stream (nats CLI runs on host, connects to exposed port)
        self._run(
            self._nats_cmd(
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
        )
    
        # Publish a message
        self._run(
            self._nats_cmd("pub survival.test 'before-restart'")
        )
    
        # docker compose down (preserves volumes) then up
        self._run("docker compose down")
        self._run("docker compose up -d")
        assert self._wait_for_healthy(max_wait=45), (
            "NATS container did not become healthy after restart"
        )
    
        # Verify stream still exists
        info_result = self._run(
            self._nats_cmd("stream info SURVIVAL_TEST --json")
        )
>       assert info_result.returncode == 0, (
            f"Stream SURVIVAL_TEST not found after restart: {info_result.stderr}"
        )
E       AssertionError: Stream SURVIVAL_TEST not found after restart: nats: error: setup failed: nats: Authorization Violation
E         
E       assert 1 == 0
E        +  where 1 = CompletedProcess(args="nats -s nats://localhost:4222 --user rich --password '' stream info SURVIVAL_TEST --json", returncode=1, stdout='', stderr='nats: error: setup failed: nats: Authorization Violation\n').returncode

tests/test_volume_persistence.py:507: AssertionError
_____________________________ TestVolumePersistenceIntegration.test_ac003_messages_retrievable_after_restart _____________________________

self = <test_volume_persistence.TestVolumePersistenceIntegration object at 0xf6fdfc84f380>

    def test_ac003_messages_retrievable_after_restart(self) -> None:
        """AC-003: Published messages are retrievable after docker compose down + up."""
        # Start and create stream with unique name
        self._run("docker compose up -d")
        assert self._wait_for_healthy(), "NATS container did not become healthy"
    
        # Create stream (nats CLI runs on host, connects to exposed port)
        self._run(
            self._nats_cmd(
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
        )
    
        # Publish messages
        for i in range(5):
            self._run(
                self._nats_cmd(f"pub retrieval.test 'persistent-msg-{i}'")
            )
    
        # Restart
        self._run("docker compose down")
        self._run("docker compose up -d")
        assert self._wait_for_healthy(max_wait=45), (
            "NATS container did not become healthy after restart"
        )
    
        # Retrieve messages — check stream info shows message count
        info_result = self._run(
            self._nats_cmd("stream info RETRIEVAL_TEST --json")
        )
>       assert info_result.returncode == 0, (
            f"Stream not found after restart: {info_result.stderr}"
        )
E       AssertionError: Stream not found after restart: nats: error: setup failed: nats: Authorization Violation
E         
E       assert 1 == 0
E        +  where 1 = CompletedProcess(args="nats -s nats://localhost:4222 --user rich --password '' stream info RETRIEVAL_TEST --json", returncode=1, stdout='', stderr='nats: error: setup failed: nats: Authorization Violation\n').returncode

tests/test_volume_persistence.py:554: AssertionError
======================================================== short test summary info =========================================================
FAILED tests/test_volume_persistence.py::TestVolumePersistenceIntegration::test_ac001_stream_creation_and_publish - AssertionError: Failed to publish message 0: nats: error: nats: Authorization Violation
FAILED tests/test_volume_persistence.py::TestVolumePersistenceIntegration::test_ac002_stream_survives_restart - AssertionError: Stream SURVIVAL_TEST not found after restart: nats: error: setup failed: nats: Authorization Violation
FAILED tests/test_volume_persistence.py::TestVolumePersistenceIntegration::test_ac003_messages_retrievable_after_restart - AssertionError: Stream not found after restart: nats: error: setup failed: nats: Authorization Violation
============================================== 3 failed, 1 passed, 21 deselected in 12.19s ===============================================
richardwoollcott@promaxgb10-41b1:~/Projects/appmilla_github/nats-infrastructure$ 
