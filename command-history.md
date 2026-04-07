/task-create create a task to: Task: Merge fleet compose addendum into parent spec
Read both files:

docs/design/specs/nats-infrastructure-system-spec.md (parent)
docs/design/specs/nats-infrastructure-spec-addendum-fleet-compose.md (addendum)

The addendum has explicit merge instructions at the top. Follow them precisely:

Update Feature 3 (Stream Definitions): Add the FLEET stream to the stream definitions table:

Stream: FLEET, Subjects: fleet.>, Retention: Limits, Max Age: 1 hour, Max Messages: 5,000, Purpose: Agent registration, deregistration, heartbeats
Add the corresponding nats stream add FLEET command to the provision-streams.sh example


Update Feature 6 (KV Stores): Add agent-registry KV bucket to the KV Buckets table:

Bucket: agent-registry, Purpose: Fleet routing table — agent capability manifests, updated on register/deregister. Jarvis reads this for routing. Survives Jarvis restarts. TTL: None (persistent)
Add TASK-27 and TASK-28 to the Feature 6 tasks


Add Feature 7: Agent Fleet Compose as a new section after Feature 6 and before Non-Functional Requirements. Include the full content from the addendum: the revised containerisation decision, the two-file compose architecture, the docker-compose.fleet.yml definition with all agent services, the scaling pattern, the agent container lifecycle → NATS registration flow, and TASK-29 through TASK-36
Update the repository structure to include the compose/ directory with docker-compose.fleet.yml and docker-compose.adapters.yml, and add fleet-status.sh to scripts/

After merging, verify the document reads as one coherent spec. The task numbering should be continuous (TASK-1 through TASK-36). Then delete the addendum file nats-infrastructure-spec-addendum-fleet-compose.md.
Task Work Complete — TASK-850A

Stack: Documentation (markdown only)
Duration: ~2 minutes

Changes made to nats-infrastructure-system-spec.md:

Acceptance Criterion	Status
FLEET stream added to Feature 3 table	Done
nats stream add FLEET added to provision-streams.sh	Done
agent-registry KV bucket added to Feature 6 table	Done
TASK-27 and TASK-28 added to Feature 6 tasks	Done
Feature 7: Agent Fleet Compose added (full content)	Done
Repository structure updated (compose/, fleet-status.sh)	Done
Task numbering continuous (TASK-1 through TASK-36)	Verified
Addendum file deleted	Done
Build Approach task ranges updated	Done
State: BACKLOG → IN_REVIEW

Next steps:

Review the merged spec for coherence
/task-complete TASK-850A when satisfied





/feature-plan "NATS Server Configuration: nats-server.conf with JetStream enabled for DGX Spark GB10" \
  --context docs/design/specs/nats-infrastructure-system-spec.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ FEATURE PLANNING COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Feature: NATS Server Configuration
Feature ID: FEAT-D2AD
Review: TASK-REV-69BD (completed)

📁 Feature file: FEAT-D2AD.yaml
📁 Implementation guide: IMPLEMENTATION-GUIDE.md
📁 README: README.md

📋 Tasks (4, sequential execution):

Wave	Task	Title	Complexity	Mode
1	TASK-NATS-001	Create nats-server.conf with JetStream	3	task-work
2	TASK-NATS-002	Create account configs + envsubst entrypoint	4	task-work
3	TASK-NATS-003	Create .env.example	2	direct
4	TASK-NATS-004	Verify NATS startup + JetStream	3	task-work
🔑 Key decisions:

envsubst for credential substitution (NATS doesn't interpolate env vars)
1GB mem / 10GB file JetStream limits (conservative for 128GB GB10)
0.0.0.0 binding safe within Tailscale mesh
curl-based verification (no nats CLI dependency)
🚀 Next steps:


/task-work TASK-NATS-001          # Start implementation
/feature-build FEAT-D2AD          # Or run autonomous build
