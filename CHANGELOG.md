# Change Log
All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](http://semver.org/).

We follow [Keep a Changelog](http://keepachangelog.com/) format.

## 0.0.1 - 2016-04-28
### Added
- Functional Proof-of-concept
  * ping-based failure detection
  * working ping-req backend (but no plumbing for checking SUSPECT nodes)
  * working gossip dissemination of messages
  * working membership modifications for adding new members to the node dict
- Pytest unit (partial coverage) and integration tests (nearly full coverage)