# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0](https://github.com/meetecho/juturna/compare/juturna-v2.1.1...juturna-v3.0.0) (2026-11-12)


### ⚠ BREAKING CHANGES

* **messages:** ObjectPayload instances with different content are no longer equal, and ObjectPayload cannot be hashed (used as a dict key or a set item) any more. The messages inside a Batch are frozen when the message that carries it is transmitted.
* **remotize:** the remote service and the Warp node must both be updated: requests of the previous protocol are refused. `juturna remotize` no longer listens on every interface: pass `--host 0.0.0.0` to serve other machines. `create_envelope` lost its `priority`, `request_type` and `response_type` arguments.
* **remotize:** send the sticky state only when the service asks for it
* **remotizer:** keep the types of meta, object payloads and batches on the wire
* **components:** Buffer, the synchronisers and Node.next_batch() are removed, together with the "sync" node configuration key (now ignored, with a warning from juturna validate), the synchroniser argument of Node.__init__ and Node.clear_buffer(). update() never receives a Message[Batch] built by the framework: messages from every upstream node arrive one at a time. Nodes that defined next_batch() must implement their policy in update() using the node state. The update worker is gone, so the worker reported in health['stuck_workers'] is now _worker_<name>.
* pipeline manager registry fix, cleanup fixed, general dead code removal
* **telemetry:** select the telemetry manager from the pipeline configuration
* freeze payload arrays and nested meta, keep zero timers and time blocks monotonically
* buffer batch selection and payload size, serialisation and draft bugs fixed
* plugin nodes changed so that the state is included in their update signature
* added state to built in node update methods
* added pipe id to envelope send and received to and from remote service
* old update signature does no longer work

### Features

* added build version to remote builder arguments ([d60af53](https://github.com/meetecho/juturna/commit/d60af53421cbe844365ef0bab38da43c503368b0))
* added builder for external and contrib plugins, removed old component builder ([e530406](https://github.com/meetecho/juturna/commit/e53040680a2e284d583e68b1129c038b7eef773b))
* added dev mode to juturna service to enable local development ([21260ab](https://github.com/meetecho/juturna/commit/21260ab213543ddda5f8f20b84c672e02380381c))
* added dev mode to juturna service to enable local development ([a48ca61](https://github.com/meetecho/juturna/commit/a48ca617775eb2e0c9e17f88d8d206d6fc0fb84a))
* added events to transport primitives ([7ec75d4](https://github.com/meetecho/juturna/commit/7ec75d46b62ef9b267947e584f28ff987a3f4299))
* added kill method to nodes and pipeline to disregard pending messages in both queue and buffer ([f39519d](https://github.com/meetecho/juturna/commit/f39519d88bff9d3c476f1433d32d982b590a7a29))
* added option in vad proc node for gpu execution ([90fab81](https://github.com/meetecho/juturna/commit/90fab81ccc928d2462d28516290052427730d12f))
* added option in vad proc node for gpu execution ([00f2670](https://github.com/meetecho/juturna/commit/00f2670b7fc1dd0d291c543374200f1a51066580))
* added pipe id to envelope send and received to and from remote service ([816da43](https://github.com/meetecho/juturna/commit/816da43fc5bc9c9eb09b78d4cf2dd6bd5b15f961))
* added telemetry endpoint to the juturna service ([74f13d1](https://github.com/meetecho/juturna/commit/74f13d1bc08c179b63bd9dba7d9dbe3cde49db62))
* added telemetry endpoint to the juturna service ([3a0c21a](https://github.com/meetecho/juturna/commit/3a0c21a8e540d6192b5d32ea171c0c2a03bcb84b))
* as per [#133](https://github.com/meetecho/juturna/issues/133) added support for both node types without requiring specific versions, thus keeping flexible support for internal and external plugins ([c7ce504](https://github.com/meetecho/juturna/commit/c7ce504e3a6c6fdbb7372d87c8dcfea0c9a97aa3))
* **components:** remove the node buffer and synchronisers ([0b532dc](https://github.com/meetecho/juturna/commit/0b532dcb696e834317d7c60b2632e68d1876f1f5))
* double import system to include both current and external as proposed in [#133](https://github.com/meetecho/juturna/issues/133), minor changes to tests and meta ([f4acdfa](https://github.com/meetecho/juturna/commit/f4acdfa0f2f8f7bb01693da162ba382416184ad2))
* env variables opt-out or defined with pattern, or readed from file ([32ed7a8](https://github.com/meetecho/juturna/commit/32ed7a843026fe9593fe900c7fdd16d30f8f3f04))
* env variables opt-out or defined with pattern, or readed from file ([267ac3c](https://github.com/meetecho/juturna/commit/267ac3c816317ed8c36915597f960981fc97f1b0))
* juturna service now exposes a route to get the main configuration parameters, useful for diagnostic ([cf0fbc5](https://github.com/meetecho/juturna/commit/cf0fbc5f2c7e3ba2ab4e6acc92e8a00c61d3ea96))
* **names:** add PixelFormat StrEnum for pixel format constants ([2c34be2](https://github.com/meetecho/juturna/commit/2c34be208c29f85fca66492ba2497ba1b2e2b45e))
* new custom filter for juturna loggers ([075cfcc](https://github.com/meetecho/juturna/commit/075cfcc4868d7c26bbee0fe5118d5f9e8d9941c0))
* **node:** notify an observer when update returns ([9a40f53](https://github.com/meetecho/juturna/commit/9a40f534cf4bc647a5be7faa50341bf1d6781112))
* nodes now receive state externally from their pipeline ([268964b](https://github.com/meetecho/juturna/commit/268964bbda6d003bf9906db84e9604cd08091035))
* **pipeline:** build only the nodes of a worker and link the others through the transport ([03a4cb7](https://github.com/meetecho/juturna/commit/03a4cb71cd1c9b37957db47e9a53e4b1a4798220))
* **pipeline:** centralize lifecycle validation and add stopped status ([6619d24](https://github.com/meetecho/juturna/commit/6619d240181e9f1df406a0530c27881cec7e4f4a)), closes [#165](https://github.com/meetecho/juturna/issues/165)
* **plugins:** added new POC transcription node using Kroko ASR ([d3fa393](https://github.com/meetecho/juturna/commit/d3fa393949b75cada0f1f92f1bfe76981e032a4a))
* **plugins:** added new POC transcription node using Kroko ASR ([f954630](https://github.com/meetecho/juturna/commit/f9546306a8b66e58c3d7679051cb9f705098dd36))
* **remotize:** leave out what cannot be sent, or fail with --strict ([a136747](https://github.com/meetecho/juturna/commit/a13674743ca6febc712191cb4d3a0fa4961d0404))
* **remotize:** leave out what cannot be sent, or fail with --strict ([b007397](https://github.com/meetecho/juturna/commit/b007397a7ded93ce815d1757e190b1062443629c))
* **remotize:** send the sticky state only when the service asks for it ([c2bf54a](https://github.com/meetecho/juturna/commit/c2bf54ac22ea5478d8359eab65f7e3c8809658e7))
* **remotize:** serve stateless warp clients behind a load balancer ([344c5e9](https://github.com/meetecho/juturna/commit/344c5e9a8e033871bf3905911a8c610ee74bcdf5))
* **remotize:** serve stateless warp clients behind a load balancer ([29c422e](https://github.com/meetecho/juturna/commit/29c422e2ea644b8bb0bc59ea82ef4270909550e0))
* **remotize:** version the remote protocol, add sessions, listen on loopback ([3fda000](https://github.com/meetecho/juturna/commit/3fda000dc6086b3a1222b46e94691a23ded8f470))
* restored old component builder for retrocompatibility, added version checker in pipeline configuration file ([22834ff](https://github.com/meetecho/juturna/commit/22834ff598151a2f7dde5e136ed086fe7b470cec))
* restored plugin hub to keep compatibility when introducing [#133](https://github.com/meetecho/juturna/issues/133) ([5317fd8](https://github.com/meetecho/juturna/commit/5317fd867039663df8b1ad0df2f80b1661e2b2ff))
* **serve:** check the token first, report client mistakes, add studio endpoints ([8c61021](https://github.com/meetecho/juturna/commit/8c61021ec7ae30ea63b8cddc4ceeb11cdce82fc6))
* **serve:** check the token first, report client mistakes, add studio endpoints ([6ca8c3d](https://github.com/meetecho/juturna/commit/6ca8c3db7a37fe3927d40b0677b0303dfe1cf0d3))
* **telemetry:** select the telemetry manager from the pipeline configuration ([649fb54](https://github.com/meetecho/juturna/commit/649fb547f94c4acd765190ffeed4e1fffbfa13cf))
* **transport:** add a browser backend based on SharedArrayBuffer and JSPI ([9287bd8](https://github.com/meetecho/juturna/commit/9287bd8b343ef9cbe55d5f703c7db186886484ee))
* **transport:** add BrowserTransport backend based on SharedArrayBuffer and JSPI ([586178b](https://github.com/meetecho/juturna/commit/586178b6a526ec6277d74c2bda8420bf7f312c30))
* **transport:** add local queues, node scope and remote destinations to the protocol ([fc54b4a](https://github.com/meetecho/juturna/commit/fc54b4ada78242d0d4fa8e242b9d8a3243d16419))
* **transport:** add the wire format between a web page and browser nodes ([5156e7f](https://github.com/meetecho/juturna/commit/5156e7fe7f9f9e269c6ff67d9b5220f019e9653b))
* **transport:** add wire codec between a web page and browser nodes ([467d547](https://github.com/meetecho/juturna/commit/467d547e7f7ddb34402f370f5e5ba48bbd5a9f66))
* **transport:** configure the transport backend from the pipeline config ([3982a7b](https://github.com/meetecho/juturna/commit/3982a7bf4df84df5efb7f8444d568cb3d9c00c5a))
* **transport:** introduce injectable transport backend for node/buffer concurrency ([68ea234](https://github.com/meetecho/juturna/commit/68ea2346f9021802a8263d6dc15eceffc49a143e))
* **transport:** let a pipeline run across several workers ([b0689d8](https://github.com/meetecho/juturna/commit/b0689d8bdecae2a8577a5d04285207826aa57913))
* **transport:** let BrowserTransport run a pipeline across several workers ([d2be389](https://github.com/meetecho/juturna/commit/d2be389e772dc0c4cfbac042a2e4988c54273e98))
* **transport:** let BrowserTransport run a pipeline across several workers ([1b925b5](https://github.com/meetecho/juturna/commit/1b925b56b132cb73c7b9a98393730ca3f89dee09))


### Bug Fixes

* added a --no-auth flag to disable token authentication when not needed ([f75496b](https://github.com/meetecho/juturna/commit/f75496bc63485cc0d8c7088305f0f70b08fa6085))
* added a basic mechanism to count successful events for node threads, and offer them as first version of node health status ([bf355f7](https://github.com/meetecho/juturna/commit/bf355f753301014d14cb10884d5c8620105988cd))
* added events to transport primitives ([19fe90a](https://github.com/meetecho/juturna/commit/19fe90aee08aac5be97e6f14080fd63894ba720a))
* added kill method to nodes and pipeline to disregard pending messages in both queue and buffer ([d51e629](https://github.com/meetecho/juturna/commit/d51e62953d77b1dbf15cec8668379dddc1eed9d8))
* added message id to message dictionary and string representation ([f6f0b3a](https://github.com/meetecho/juturna/commit/f6f0b3a4beca6108c2b270e23dfdade2102e8ece))
* added state to built in node update methods ([d6ce9f9](https://github.com/meetecho/juturna/commit/d6ce9f9d8d1c7d59b0b04105332af02f97c63057))
* added transaction rule for pipeline killing, fixed issue with thread waiting timeout using sentinel value to exit queue waiting, similar to old poison pill ([d189099](https://github.com/meetecho/juturna/commit/d1890994054d7c84f3b345e04f21e70149970cef))
* **audio_file:** _generate_chunks source function returns a ControlPa… ([4f5cbb4](https://github.com/meetecho/juturna/commit/4f5cbb4a0f7d0c902c7801e3eaf21f3f83788dae))
* **audio_file:** _generate_chunks source function returns a ControlPayload instead of None ([f70c202](https://github.com/meetecho/juturna/commit/f70c202d72c27ebaa6ef11e2a2a02b180c923b1a))
* **audio_rtp_av:** flush buffer handling in audio_rtp_av node ([b279c72](https://github.com/meetecho/juturna/commit/b279c72c5debaf117eb72383cd46fa3125622029))
* **audio_rtp_av:** guard rtp thread join against a None handle ([91c9f90](https://github.com/meetecho/juturna/commit/91c9f904ee788a7f1438c3ed13dfd00de061e70e))
* **audio_rtp_av:** handled inconsistent dtype [#173](https://github.com/meetecho/juturna/issues/173) ([d6b3ed8](https://github.com/meetecho/juturna/commit/d6b3ed8069906b6d2a16fb7c8332e7cb4ef0c7ee))
* **audio_rtp_av:** pending queue now adpt to resampler_format ([5858a6b](https://github.com/meetecho/juturna/commit/5858a6bd9b4d0b30dbb9227cf7f73aa0c1e8a089))
* **audio-rtp-av:** respect resampler format dtype and handle multi-channel audio correctly ([f5ea993](https://github.com/meetecho/juturna/commit/f5ea9931534cdb14ead17a5ce7c90f986272efd2))
* avoid private telemetry thread state ([f28c76b](https://github.com/meetecho/juturna/commit/f28c76b3da70f02d843877c34a7a9c7a28d9d298))
* avoid private telemetry thread state ([543e90a](https://github.com/meetecho/juturna/commit/543e90a502d848fa9afe5bd9d3a001b5ab721b01))
* block every ObjectPayload mutator and compute its size lazily ([c73567f](https://github.com/meetecho/juturna/commit/c73567f281efcfa39b6db7ab2ad67a16a5cd213f))
* buffer batch selection and payload size, serialisation and draft bugs fixed ([64b81d0](https://github.com/meetecho/juturna/commit/64b81d05dec41548deb9ea09b043aa1a71d65a38))
* checking duplicate nodes when warming up or validating a pipeline ([7d52a30](https://github.com/meetecho/juturna/commit/7d52a302793533ab02849ec721849bc4cf56a0f4))
* configured Dockerfile and project file for node migration ([9dd55a9](https://github.com/meetecho/juturna/commit/9dd55a9886fc58b6de52a1f49e1d49a65c79525d))
* **core:** always send ControlPayloads to buffer ([997f411](https://github.com/meetecho/juturna/commit/997f411761a7503a97c4743dc32a09a1f1bb4f8c))
* explicitly converting tensor to numpy array for extracted audio chunks ([29427ee](https://github.com/meetecho/juturna/commit/29427ee02f49ff1bc1c1e69759976777418bb3f8))
* fixed leftover comments ([af01e2c](https://github.com/meetecho/juturna/commit/af01e2c0751b70b3b78cee187c8f499b663e5df2))
* freeze payload arrays and nested meta, keep zero timers and time blocks monotonically ([8cbd135](https://github.com/meetecho/juturna/commit/8cbd13585d1843f19587072557fea0a1ccc0eb81))
* http service now requires a token and restricts allowed env vars in remote configurations ([ed0cea5](https://github.com/meetecho/juturna/commit/ed0cea54cff15b41e9cf9b3ae62cf64321b66b95))
* **json_http:** avoid hanging shutdown when the server never started ([b6ba597](https://github.com/meetecho/juturna/commit/b6ba5975b4c183229097d1a5b192fdb556349813))
* **json_websocket:** accept text frames from the websocket client ([a7c1f07](https://github.com/meetecho/juturna/commit/a7c1f074019d378c6b32a907a612c25466ee64a2))
* **json_websocket:** stop shadowing the node inbound queue ([42a602e](https://github.com/meetecho/juturna/commit/42a602ecd7bcd6398e2d40a12b1762681ba07681))
* kill does not hang when update method gets stuck ([a13bf6f](https://github.com/meetecho/juturna/commit/a13bf6f79163c8843a1ddecc23157716a7fcf1f8))
* kill does not hang when update method gets stuck ([1f6c343](https://github.com/meetecho/juturna/commit/1f6c3437166d86b730bb24ca7b8cb703ec2bb3d9))
* license attribution properly set ([9f9981b](https://github.com/meetecho/juturna/commit/9f9981b2cc752609618b078406c0f7302942ac6a))
* license attribution properly set ([b96f4cb](https://github.com/meetecho/juturna/commit/b96f4cb2d41983a37e38f6a726e69289bf484684))
* make juturna.hub and juturna.remotizer lazy imports ([03e6b89](https://github.com/meetecho/juturna/commit/03e6b892a0b36a695711c25d43d55fc003896d2a))
* make juturna.nodes a lazy import ([f2e9945](https://github.com/meetecho/juturna/commit/f2e9945a0c6f7708af7c71f7e65934417c932bfa))
* make juturna.nodes, juturna.hub and juturna.remotizer lazy imports ([e5140c2](https://github.com/meetecho/juturna/commit/e5140c2a8704a654df395d1ed60988b4cf882664))
* **messages:** compare ObjectPayload by content, copy and pickle frozen messages ([a289fd6](https://github.com/meetecho/juturna/commit/a289fd643c7757255a395843043e643710cf0992))
* mockup for new update thread and worker thread ([456d1e9](https://github.com/meetecho/juturna/commit/456d1e98d0d4cfa9e87cfbd765a5dc6aa028fdeb))
* narrowing the target exception to av-specific issue with invalid data ([76fb0ac](https://github.com/meetecho/juturna/commit/76fb0ac6308b2564d83f7e0c5b45652f34b7c55b))
* narrowing the target exception to av-specific issue with invalid data ([9608f0c](https://github.com/meetecho/juturna/commit/9608f0c8715f56ef2d9512e959c0b529e90a41f1))
* node draining now properly completes at stop ([4a6d8bb](https://github.com/meetecho/juturna/commit/4a6d8bb6d272f821c0583d0cd0001abb0e36b5e7))
* node draining now properly completes at stop ([dd4185a](https://github.com/meetecho/juturna/commit/dd4185a4820b3f076b055e947d98b60b20c11a7e))
* node state properly added to envelope, fixed bugs with evenlope ids ([116d099](https://github.com/meetecho/juturna/commit/116d099a9cd176284579342e22d3aee77e0efdbe))
* **node_rtp_av:** expose configuration and add requested flush ([ea283a5](https://github.com/meetecho/juturna/commit/ea283a521824e71ed5002ce9494e762819369fce))
* **node:** queue timers are now capped to JUTURNA_THREAD_JOIN_TIMEOUT ([e46d237](https://github.com/meetecho/juturna/commit/e46d2370785e96d71531268934f3b7d1b37e2237))
* **nodes:** harden node shutdown and route node-owned workers through the transport ([8ace2c0](https://github.com/meetecho/juturna/commit/8ace2c047fe7008d131f5b4031a5b388f5e8e13f))
* **node:** skip messages the state resolver drops ([c165f4f](https://github.com/meetecho/juturna/commit/c165f4fa3250e95f3c35740bc1d920391746af60))
* **node:** skip messages the state resolver drops ([a4ae3e0](https://github.com/meetecho/juturna/commit/a4ae3e07c988f592d4ca14600f720828a9efd029))
* **nodes:** log swallowed exceptions and fix ffmpeg sink shutdown ([5e95071](https://github.com/meetecho/juturna/commit/5e950714963322b3678ca592057b150884fc55c9))
* **notifier_http:** bound stop() drain time against an unresponsive endpoint ([6e51d31](https://github.com/meetecho/juturna/commit/6e51d313f60b418840caad5a52e41389b1dbdb0c))
* **notifier_http:** keep the pipe_id reference alive after the parsing ([299f78a](https://github.com/meetecho/juturna/commit/299f78aff4ce858be3bdaaf6eba76f79da7700c0))
* **notifier_http:** keep the pipe_id reference alive after the parsing ([b316a44](https://github.com/meetecho/juturna/commit/b316a4404b3574df823e4ffcfa3e495f22129664))
* **notifier-websocket:** reuse persistent connection with retry on send ([7aabd1d](https://github.com/meetecho/juturna/commit/7aabd1dfd846146723d21d922de3ee58cb9ce3b3))
* **notifier-websocket:** reuse persistent connection with retry on send ([4835763](https://github.com/meetecho/juturna/commit/48357637ba102283644ebc1fdc544d576a59c542))
* **payloads:** make ObjectPayload picklable without allowing mutation ([6cbc333](https://github.com/meetecho/juturna/commit/6cbc333e7624dcecdbd1951681037bc9c4f42ab2))
* pipeline manager registry fix, cleanup fixed, general dead code removal ([ea77675](https://github.com/meetecho/juturna/commit/ea77675bdacade784fdef95bfb110ab93da12821))
* **pipeline:** decouple status claim from transition completion ([5181fee](https://github.com/meetecho/juturna/commit/5181fee2a2910afc96f4879e7e25712f54f74488))
* **pipeline:** enforce the env allowlist where values are resolved ([87a427c](https://github.com/meetecho/juturna/commit/87a427c50a01481b969417e82d0f9acbf7361918))
* **pipeline:** stop every node when one fails, let kill() cut a stop ([4e97cc9](https://github.com/meetecho/juturna/commit/4e97cc94ac9d91db2e3e28ec579901aa455c51f3))
* **pipeline:** stop every node when one fails, let kill() cut a stop ([2830420](https://github.com/meetecho/juturna/commit/283042078a976a196b4141f408a30db8ba194f0d))
* pipes are checked for cycles when warming up, instead of silently skipping unreachable nodes ([4c2f77a](https://github.com/meetecho/juturna/commit/4c2f77acf6bc33f9dddccce54b8902e90a66916a))
* plugin nodes changed so that the state is included in their update signature ([1c86220](https://github.com/meetecho/juturna/commit/1c86220802d6ce7c2843dfe551a89580cbd4e950))
* prevent kill from hanging in case of saturated queues ([1c1d585](https://github.com/meetecho/juturna/commit/1c1d5856e03f56c2ec882b9b01cf694dc2d8f3c4))
* prevent source loop from spinning on None or failing sources ([4362a33](https://github.com/meetecho/juturna/commit/4362a3310479b3018b2f7681ade4b01ab79d4ba9))
* prevent source loop from spinning on None or failing sources ([4049898](https://github.com/meetecho/juturna/commit/4049898a005cdef47004f0eb349adea9176897c2))
* registered log extras can now be deregistered, reserved keys not allowed in extras ([e243b2f](https://github.com/meetecho/juturna/commit/e243b2fec959410cf24cb5fa7480bb738adda4a4))
* reject pipeline, node and telemetry names that escape their folder ([98a5424](https://github.com/meetecho/juturna/commit/98a54248db290b41067be7ae57f27bd23ceb410e))
* remote service swaps node state per request while earlier reques… ([b5d0ccf](https://github.com/meetecho/juturna/commit/b5d0ccfeaf0bca3c3b0929329580583a4a9f1fe5))
* remote service swaps node state per request while earlier requests are still processing ([4e7215b](https://github.com/meetecho/juturna/commit/4e7215bb4d26dbc17146f5b6302609ec9436da40))
* **remotize:** preventing reply mixup from remote ([298a624](https://github.com/meetecho/juturna/commit/298a624778dc701f211fe4ff5d5650efe2919f94))
* **remotize:** preventing reply mixup from remote ([82fade4](https://github.com/meetecho/juturna/commit/82fade4c805ce948e7dbf295a2f7a49470017123))
* **remotize:** report every loss of a remote response ([92cc573](https://github.com/meetecho/juturna/commit/92cc5730598767536c5f0e0ec0947636da8de7c3))
* **remotize:** report every loss of a remote response ([75e7529](https://github.com/meetecho/juturna/commit/75e75299bebddaf6fb9382ea786e47b473229be4))
* **remotizer:** json-encode envelope state instead of assigning a dict ([2c7b3c2](https://github.com/meetecho/juturna/commit/2c7b3c2680087b7ea44cba83b2d8bcbe2befd14f))
* **remotizer:** json-encode envelope state instead of assigning a dict ([b8b9be8](https://github.com/meetecho/juturna/commit/b8b9be877abdac3a9743a8939088ca2d6d7ae895))
* **remotizer:** keep the types of meta, object payloads and batches on the wire ([5814046](https://github.com/meetecho/juturna/commit/5814046f784ef2c0df2237b8bb1f9db6e5e37e07))
* removed control scaffolding in node thread control ([d658679](https://github.com/meetecho/juturna/commit/d658679d1fa82dcf7585e71249d5e8d6910f3e3a))
* removed hardcoded version assignment when creating pipe configuration from CLI ([4aa616e](https://github.com/meetecho/juturna/commit/4aa616ec0dd410d5defbc34943932de315a0d893))
* removed leftover comment ([e1ece32](https://github.com/meetecho/juturna/commit/e1ece32f93c72f38451bd6dad1ad2faa97b4bcbf))
* removed old reference to batch ([8e82ad9](https://github.com/meetecho/juturna/commit/8e82ad942aa73d1e6d24799a64f924ca96302305))
* replaced component builder with new builder for remotizer ([c2b1249](https://github.com/meetecho/juturna/commit/c2b124919ca4f11ebc2ebe487983cfc6fb651885))
* rollback a failed warmup and reject duplicate links ([5cdaae6](https://github.com/meetecho/juturna/commit/5cdaae6536acd621b5ad44bedfa77fa27bce47b8))
* rollback a failed warmup and reject duplicate links ([ffa55e1](https://github.com/meetecho/juturna/commit/ffa55e111523975529e99b5a6281b3d0a6494d40))
* rollback started nodes when pipeline start fails ([db28e72](https://github.com/meetecho/juturna/commit/db28e722c2bb56d2336ff8a95ca40f5cc2823c5a))
* rollback started nodes when pipeline start fails or gets interrupted ([1a79b6e](https://github.com/meetecho/juturna/commit/1a79b6e28ebe964d287f9fddddc3fb43c05093ea))
* safely decoding received packets in audio rtp av node, closes [#174](https://github.com/meetecho/juturna/issues/174) ([c9f10da](https://github.com/meetecho/juturna/commit/c9f10da18dd271aad8263951bf6f693cf1b534d6))
* source id cannot be incorrectly assigned to frozen messages ([27e906b](https://github.com/meetecho/juturna/commit/27e906b267574579c8651838048ed84794385e7c))
* **sources_rtp_av:** expose configuration and add requested flush ([911502e](https://github.com/meetecho/juturna/commit/911502e5097b72b69cf37534aad685598aae3eec))
* stub command aligned to work with new node design, tests properly aligned and leftovers from previous implementation removed ([494234a](https://github.com/meetecho/juturna/commit/494234abf7fc0525e0957ea6e859240a2d15a90b))
* **telemetry:** guard the memory records with a lock ([c728f1f](https://github.com/meetecho/juturna/commit/c728f1f96c0a86b5da7d02067991a529a5b0801d))
* **telemetry:** guard the memory records with a lock ([83bb953](https://github.com/meetecho/juturna/commit/83bb9534ecb690d298d756b7f70858dd4519d762))
* **transcribers:** use safe access for VAD metadata in message.meta ([11770ae](https://github.com/meetecho/juturna/commit/11770ae204c3834e6a10a6e1421796e18480ddcb))
* **transcribers:** use safe access for VAD metadata in message.meta ([03a7061](https://github.com/meetecho/juturna/commit/03a706171af4878ffeafe8cf5dca40a0749bfae0))
* **transport:** allocate the browser lock cell on first use ([2191793](https://github.com/meetecho/juturna/commit/2191793d77c8e85a8b9d7fc94937e7a9f0046ab9))
* **transport:** drop unused Event primitive, fix qsize() return type ([0e0cd2a](https://github.com/meetecho/juturna/commit/0e0cd2a9150e436e62aefe020df53379c316e3a7))
* **transport:** drop unused signal ([a9d6388](https://github.com/meetecho/juturna/commit/a9d63883183c1fcd9c2f39301f9d091e0f6af975))
* **transport:** replace Event in __init__ ([5ff99c5](https://github.com/meetecho/juturna/commit/5ff99c5aae10e54c59ec5696dda331f82d9ea943))
* **transport:** replace Event in telemetry ([3510d17](https://github.com/meetecho/juturna/commit/3510d170e5b827bcd41176bfaf3619358314ae34))
* **transport:** restore event in place of signal ([b2830de](https://github.com/meetecho/juturna/commit/b2830dec2fa5d49048b49f76188101528a1de24a))
* updated signatures for test plugins ([2e36e1e](https://github.com/meetecho/juturna/commit/2e36e1e14bb4a8e1e39f11581365d513f1571c60))
* validate CLI now properly reports faulty configurations ([b92fa2f](https://github.com/meetecho/juturna/commit/b92fa2f499bc8f2103d3973ef68a48443972ed06))
* validate CLI now properly reports faulty configurations ([9df5f41](https://github.com/meetecho/juturna/commit/9df5f418b0822b5f78e6e91225884d63c3838890))
* **video_rtp_av:** apply a read timeout so stop() cannot hang forever ([57dcb44](https://github.com/meetecho/juturna/commit/57dcb444242c8dd9cc682e4163ed91d9e8241f2b))
* **video_rtp_av:** expose configuration ([dc9109a](https://github.com/meetecho/juturna/commit/dc9109ab55f83557467b9aa86ca524b39b950b1a))
* whenever user code us executed through a node thread (update, source, transmit), a try-catch block now makes sure the node does not crash and goes black, but rather records the failure and uses a counter to determine how many failures a node registered ([bb6b114](https://github.com/meetecho/juturna/commit/bb6b114daf9e95bd6c6812f00d5d20f4054fbb08))


### Reverts

* **docs:** drop pipeline lifecycle doc changes from PR ([2db9454](https://github.com/meetecho/juturna/commit/2db9454b7d1251c9c3d26da280bf9a6b9e11b42e))


### Documentation

* added build instruction for image build content ([1cacb7c](https://github.com/meetecho/juturna/commit/1cacb7c64804597a5cbd4bbe91ec73efe3ecc817))
* fixed typo in virtual env code example ([d1f6cdc](https://github.com/meetecho/juturna/commit/d1f6cdc6c74b6af79675bcce3ac12255b4b536fe))
* fixed typo in virtual env code example ([120046b](https://github.com/meetecho/juturna/commit/120046b1a672914bc9090278fed26580f3530401))
* **pipeline:** pipeline lifecycle detailed, add basic use_cli page ([6b83c61](https://github.com/meetecho/juturna/commit/6b83c610f2ccb6d93a68260c62c143a5ba5291a2))
* rewrite the documentation for 3.0 ([6b7447f](https://github.com/meetecho/juturna/commit/6b7447fdde2205a7dc711ddc2ba70debcbf40a51))
* rewrite the documentation for 3.0, add a tutorial and a migration guide ([1986303](https://github.com/meetecho/juturna/commit/1986303c5de00c25c7a855a8c9769ab57606677e))


### Code Refactoring

* cleaning useless properties in base node class and made corresponding properties public ([208e45a](https://github.com/meetecho/juturna/commit/208e45aa5da8a7092c90cd7c367489c6facd2632))
* **components:** move exceptions into components.exceptions subpackage ([31ffb05](https://github.com/meetecho/juturna/commit/31ffb053a393fc68d593f3c9a6982410e50ebb9c))
* implemented installable node logic for node building and cli tools ([f11438b](https://github.com/meetecho/juturna/commit/f11438b7d0782d2bb57ee9018bc239d0e7e46468))
* **names:** use match blocks in PixelFormat helpers ([2ddfa30](https://github.com/meetecho/juturna/commit/2ddfa3035a801445ab1219e866d4f282fca5f0ef))
* **names:** use match blocks in PixelFormat helpers ([ead1c68](https://github.com/meetecho/juturna/commit/ead1c6892966598357d6b5d811ce0dfd8c95b699))
* **node:** improve node lifecycle management and graceful shutdown ([7243da9](https://github.com/meetecho/juturna/commit/7243da93772337e2f112996a8e9829fb94e31f21))
* **nodes:** route node-owned workers through the transport backend ([ba23ce5](https://github.com/meetecho/juturna/commit/ba23ce5348b50725a9dababf024c13a03951982d))
* **pipeline:** move lifecycle states into a dedicated object ([5129753](https://github.com/meetecho/juturna/commit/5129753128bc093f16c18dffe072632d28af2987))
* **remotizer:** use protobuf Struct for envelope state field ([03e2745](https://github.com/meetecho/juturna/commit/03e2745ae73802e15db0527fb31049a00b3e2458))
* remove useless coupling date between nodes ([b94cc63](https://github.com/meetecho/juturna/commit/b94cc63962a46bcaf3d27d809f219920aedb9505))
* remove useless coupling date between nodes ([10bf880](https://github.com/meetecho/juturna/commit/10bf880b2030c1a6c7fd6a52cc9fa983e87807cd))
* removed all nodes from the juturna structure, both built-in and plugins ([e2d89c3](https://github.com/meetecho/juturna/commit/e2d89c3dcb3450f8a17157b05d96d5a4b576f2e1))
* rollback failed start through abort_transition ([f8c124b](https://github.com/meetecho/juturna/commit/f8c124bb32c059bc2e18f90a03acafad05bf129e))
* state is now passed among kwargs so that extending node signature will not require changing it ([da6e910](https://github.com/meetecho/juturna/commit/da6e9101bfe84f7c38f1e88173ff09d2ecfacb18))
* **telemetry:** route TelemetryManager through the transport backend and fix buffer races ([0ff43eb](https://github.com/meetecho/juturna/commit/0ff43eb90348ec777a0e7c2bc9cc96911047d17c))
* **telemetry:** route TelemetryManager through the transport backend and fix buffer races ([e8770ef](https://github.com/meetecho/juturna/commit/e8770ef15a31be7f991c1e98fcd93b595919a412))
* **transport:** move transports in submodule ([f337f26](https://github.com/meetecho/juturna/commit/f337f26bc4bff74b98fb515e15a7a75a74e55cb1))
* **transports:** move each transport in a separate subpackage ([ece2942](https://github.com/meetecho/juturna/commit/ece2942d7f052e9f02b09b0aaf59a126599fbed0))
* **transport:** split each transport into simpler roles ([89532bb](https://github.com/meetecho/juturna/commit/89532bbac7b108d6c3b54e315da50b10ddd5e755))

## [2.1.1](https://github.com/meetecho/juturna/compare/juturna-v2.1.0...juturna-v2.1.1) (2026-04-14)


### Bug Fixes

* **deps:** updating dependencies to avoid conflicts in ([6edbe12](https://github.com/meetecho/juturna/commit/6edbe123e6717bdd1de60410016986a1eed79953))
* **faster-whisper:** reverting nvidia library version to 12 ([fe9a501](https://github.com/meetecho/juturna/commit/fe9a501dc257a7c8647497bdf27bc1ca8e010a5e))
* **faster-whisper:** reverting nvidia library version to 12 ([3593672](https://github.com/meetecho/juturna/commit/35936728884abe64eff641a973aec4ffcc7e835b))
* patched typo in warp node import path ([8a0368a](https://github.com/meetecho/juturna/commit/8a0368a868afcd5e857d5f12e18e63a7d19b84b2))
* patched typo in warp node import path ([9be3c0b](https://github.com/meetecho/juturna/commit/9be3c0b27a8c4e6aae55f46e41de06860c54e2a3))


### Documentation

* added short reference to virtual envs in installation guide ([83b8974](https://github.com/meetecho/juturna/commit/83b89749a65aa20fa1b3a7c4afd7c6b334a9a16e))
* added short reference to virtual envs in installation guide ([022338c](https://github.com/meetecho/juturna/commit/022338c8566334b2d18e9408235c5bbd2cdb2270))

## [2.1.0](https://github.com/meetecho/juturna/compare/juturna-v2.0.0...juturna-v2.1.0) (2026-04-08)


### Features

* added plugin source node for csv feeding ([e3c92fd](https://github.com/meetecho/juturna/commit/e3c92fd49fdae1bded9bdd866e41595c80ae48e0))
* **API:** add dedicated exception and handlers for pipeline endpoint errors ([ed4e825](https://github.com/meetecho/juturna/commit/ed4e825b0e412aa1aa14e699adcfa4550b0b72ce))
* **API:** add pipelines/deploy endpoint ([5ca640d](https://github.com/meetecho/juturna/commit/5ca640d07667694aa7d2d9fdab63748c1d8afe6a))
* **core:** added in proc utils a decorator to safely run node code preventing it to fail ([f307d26](https://github.com/meetecho/juturna/commit/f307d2665466c95055d1f14176cd0e28aed437b4))
* custom header and header skipping ([4d6b14a](https://github.com/meetecho/juturna/commit/4d6b14a7faedbdef5cc4f6e66cf3f5c15c72c4b9))
* custom header and header skipping ([b443969](https://github.com/meetecho/juturna/commit/b443969e4d3e91501604c64aad94bed83c1d684f))
* lauching a pipe from the cli now exits once all nodes in the pipe are stopped ([5df8517](https://github.com/meetecho/juturna/commit/5df8517e1c70c0bda764ccf96eb9131c4354d457))
* ollama node updated with external configuration file ([2205dae](https://github.com/meetecho/juturna/commit/2205dae1a13cf15d20a339d734bcc6919ec33815))
* **plugins:** added new summarization node that generate progressive summaries ([b7632f7](https://github.com/meetecho/juturna/commit/b7632f70f01dcf8a73ef66c47db05977635620ee))
* **plugins:** fixed a bug in summarizer for non dictionary response ([17de6f6](https://github.com/meetecho/juturna/commit/17de6f6a0e2d061c37a9239d5635c14ff4873099))
* **plugins:** fixed a bug in summarizer when model returns malformed response ([2016b4f](https://github.com/meetecho/juturna/commit/2016b4feab30fde05e685f991456a62b523fbc92))
* **plugins:** fixed improper dict in topic history ([46e114b](https://github.com/meetecho/juturna/commit/46e114bdb7284dabdd7d1dc67b3bee80ed63847f))
* **plugins:** fixed improper dict in topic history ([aaace56](https://github.com/meetecho/juturna/commit/aaace5625536571998a42476c016e41cb582a407))
* **plugins:** summarization node now manages multi-topic history ([e391bae](https://github.com/meetecho/juturna/commit/e391bae37a3735ace0891cb0ad5c87d6fa8cd320))
* **plugins:** temperature added for ollama models ([a7460fe](https://github.com/meetecho/juturna/commit/a7460fe077f0ed18260932bf400a9f875e04c1c7))
* prompter node now can buffer input messages ([d06a683](https://github.com/meetecho/juturna/commit/d06a6838a62e248cb13fd77fe9f08a1fed30c960))


### Bug Fixes

* **API:** move models module under cli/commands to satisfy dependencies ([7d7c1b6](https://github.com/meetecho/juturna/commit/7d7c1b6b005f509ba6e864e3df3bee045e33e52f))
* changed the type of message built in the handler for the json websocket source node, fixes [#123](https://github.com/meetecho/juturna/issues/123) ([af42010](https://github.com/meetecho/juturna/commit/af420105f46a7008ba56d9b5344c2d54b43b3283))
* changed update signature and class name for json http source node, fixes [#122](https://github.com/meetecho/juturna/issues/122) and [#124](https://github.com/meetecho/juturna/issues/124) ([2a49ffa](https://github.com/meetecho/juturna/commit/2a49ffafa9514dddba3cfc55f3b9a83fb55c3e57))
* fixed queue management for builtin http node ([74bff20](https://github.com/meetecho/juturna/commit/74bff20fdd5ba200ca277681eb34c89ce923cff9))
* mongo sink node updated to use latest library changes ([9e629d7](https://github.com/meetecho/juturna/commit/9e629d7572871b448ff2821796efa47e0303c2b1))
* mongo sink node updated with connection timeout ([f660e92](https://github.com/meetecho/juturna/commit/f660e926b37339ebaf105eb57d7796319b10cf49))
* ollama proc node now includes the full input payload in its transmitted messages ([c9b2954](https://github.com/meetecho/juturna/commit/c9b29547c5d2bec7857d3185ebdb24a2b223c4ad))
* synced node signatures with head ([7cece5c](https://github.com/meetecho/juturna/commit/7cece5c1a76cdb8a5075e3944fd4e99bccf7e098))
* telemetry writer now checks for availability of size field as per [#140](https://github.com/meetecho/juturna/issues/140) ([d3e9d5f](https://github.com/meetecho/juturna/commit/d3e9d5f8204b42b5b80c18914d57dcdefe3494e2))


### Code Refactoring

* **API:** standardize responses on PipelineManager methods; manage exceptions on api calls ([0168f63](https://github.com/meetecho/juturna/commit/0168f6357a594bcf8b103d731ce9749fc299432b))

## [2.0.0](https://github.com/meetecho/juturna/compare/juturna-v1.0.2...juturna-v2.0.0) (2026-02-19)


### Features

* ([#21](https://github.com/meetecho/juturna/issues/21)) address requested changes from review ([68eff99](https://github.com/meetecho/juturna/commit/68eff99c3dc5a8415f1d7b2c815bc69db6269ea2))
* ([#21](https://github.com/meetecho/juturna/issues/21)) address requested changes from review ([0f9c70b](https://github.com/meetecho/juturna/commit/0f9c70b486ccc73f45f3843add9d3f42d9277fdd))
* add environment variable support for pipeline configurations ([9baf369](https://github.com/meetecho/juturna/commit/9baf369049deff97b51e3b3f594ea8ab1168c022))
* add environment variable support for pipeline configurations ([aed144e](https://github.com/meetecho/juturna/commit/aed144e056885512bbc8e52d7813404dcfef866d)), closes [#38](https://github.com/meetecho/juturna/issues/38)
* added rescaling and resizing options for image reader source node as per [#90](https://github.com/meetecho/juturna/issues/90) ([f34f88d](https://github.com/meetecho/juturna/commit/f34f88d0fecc943db5560476eaf9f08c19512ffa))
* added source node for remote rtp video streams using pyav ([5e04f36](https://github.com/meetecho/juturna/commit/5e04f364e318baadba835fdef799caea795e96f6))
* adding new cli to collect all dependencies of a pipe as per [#118](https://github.com/meetecho/juturna/issues/118) ([74daa85](https://github.com/meetecho/juturna/commit/74daa8581eb2cf28f92d2a1fd4a75eb7aefd92d7))
* **audio_rtp:** make RTP encoding, clock rate, and channel count configurable in source node ([313e318](https://github.com/meetecho/juturna/commit/313e3187c60762222bf677525dd0b8cc9135f4c6))
* auto dump feature for nodes as specified in [#115](https://github.com/meetecho/juturna/issues/115) ([fa2117a](https://github.com/meetecho/juturna/commit/fa2117ae9273423f9ee0268738693d78f66b9af0))
* **buffer:** add buffer flush method ([1a0f7b1](https://github.com/meetecho/juturna/commit/1a0f7b1fe10c9d50d759b1b6e44e5e4ca3413c39))
* **buffer:** add buffer flush method ([be7041f](https://github.com/meetecho/juturna/commit/be7041f91e70712f56394eba570ecdfbf8b92c51))
* **core:** added comment to control signal module to indicate that any signal less than zero will trigger the stop function on receiving nodes ([1168164](https://github.com/meetecho/juturna/commit/11681641719c7e4e58c87ba51f0ad0a5bd995070))
* **core:** added control payloads to be used within nodes ([ea2b88c](https://github.com/meetecho/juturna/commit/ea2b88cc2f85bbc78d7ca79e1d97378d089ee1fc))
* **core:** added control payloads to be used within nodes to perform actions based on control messages as requested in [#44](https://github.com/meetecho/juturna/issues/44) ([961a45c](https://github.com/meetecho/juturna/commit/961a45cfa30c30e2190ca2c66799262d72b5d624))
* for [#115](https://github.com/meetecho/juturna/issues/115) dumping a message is now best effort, so the node will not crash if the message contains non serialisable content (possible in meta values) ([5e0f2f5](https://github.com/meetecho/juturna/commit/5e0f2f5fa24af27827bbc28fe54bea36c0f5e5e8))
* handling subprocess unattended termination with possibly respawn in nodes/soruce/audio-rtp ([265c215](https://github.com/meetecho/juturna/commit/265c21587ba5e28401d99f71d935e54124d45a6b))
* make ffmpeg log level configurable  in nodes/soruce/audio-rtp ([29c1e90](https://github.com/meetecho/juturna/commit/29c1e90cf7b76c9e144bf5cd3ea03fc0eab3ead7))
* max queue size can be set through the JUTURNA_MAX_QUEUE_SIZE envar ([dc3f95f](https://github.com/meetecho/juturna/commit/dc3f95f6ad742d02ee075da4d00b200ecf951aed))
* **node:** added audio format to audo payloads produced by audio rtp node with av ([c0e108a](https://github.com/meetecho/juturna/commit/c0e108a307c15633fafddc8bae5519d23a4324bc))
* **node:** added new pyav audio rtp source node ([dcc2fa9](https://github.com/meetecho/juturna/commit/dcc2fa9e087fcbe33759caffff5ad85b70511f18))
* **node:** added new pyav audio rtp source node ([58885f3](https://github.com/meetecho/juturna/commit/58885f326dad4b26d018e34c541c02edd23ea747))
* **node:** fixed unused arguments for pyav audio source node and removed useless audio format conversion ([91cecd2](https://github.com/meetecho/juturna/commit/91cecd217545ca201d20a66988816d44394c7e14))
* nodes now keep track of data ids that resulted in a data transmission event ([d1b7a4b](https://github.com/meetecho/juturna/commit/d1b7a4bfd173ffc5b9c67150eecb0db4926bcfb2))
* **payload:** add a AnyPayload sugar type ([e646712](https://github.com/meetecho/juturna/commit/e64671217ee0082895c753554fb2c1f9910fa750))
* **pipeline:** use DAG layers for deterministic node startup order ([49a9f4c](https://github.com/meetecho/juturna/commit/49a9f4ccd5afd998f25bfafbeb42a13a545865b3))
* **pipeline:** use DAG layers for deterministic node startup order ([d4f4cf6](https://github.com/meetecho/juturna/commit/d4f4cf6c582d39092accdd161c0915a2c6805b58))
* telemetry skeleton added for nodes to record basic statistics about received and transmitted messages as per [#83](https://github.com/meetecho/juturna/issues/83) ([c426ffa](https://github.com/meetecho/juturna/commit/c426ffaba390f05e10835bd7821ae4eeaa4cec87))
* telemetry skeleton added for nodes to record basic statistics about received and transmitted messages as per [#83](https://github.com/meetecho/juturna/issues/83) ([ec539f2](https://github.com/meetecho/juturna/commit/ec539f21feb387cb6d24f5cd97d524dffe7a085f))
* **warp:** add initial warp node implementation ([2dfa8dc](https://github.com/meetecho/juturna/commit/2dfa8dcbeeb02dc33e97c14c05ddf395e7fe1f01))
* **warp:** implement async remote service and fix serialization ([90a84a9](https://github.com/meetecho/juturna/commit/90a84a92ddfa1c943866cbb652f540337c39a229))
* **warp:** massive code refactoring ([71a6dc5](https://github.com/meetecho/juturna/commit/71a6dc5ee9915beea35990e3e1e7d267adfddf89))
* **warp:** rely on internal tracking_id to match remote in/out messages ([8d5cd63](https://github.com/meetecho/juturna/commit/8d5cd63426dcabacc3ef58681511786835558ba4))
* **warp:** Replace correlation_id with internal message-based tracking ([10351db](https://github.com/meetecho/juturna/commit/10351dbb4e221a3ad0207bfdebe4d853cb68f22d))
* **yolo-detector:** add a new YOLO node ([990fe4a](https://github.com/meetecho/juturna/commit/990fe4a7041cb1b2c5c2b0c8b0ebb0707bb46725))
* **yolo-detector:** pick the right normalization branch ([8f6c957](https://github.com/meetecho/juturna/commit/8f6c9573dd78cd0ec0ce83ef021995fc7590011f))
* **yolo-detector:** predict uses the max(height,width) as imgsz ([568b2b6](https://github.com/meetecho/juturna/commit/568b2b65de4d739bf45fd02a46e71a10fb9c2fda))


### Bug Fixes

* ([#25](https://github.com/meetecho/juturna/issues/25)) inferring the incoming audio channels by parsing the encoding_clock_channel parameter ([3902cbe](https://github.com/meetecho/juturna/commit/3902cbe60008ecf393f5c0705d1ea3ec929996b5))
* added audio format to AudioPayload class ([c9d0a4a](https://github.com/meetecho/juturna/commit/c9d0a4ac5fd56a054e23d2df61d50b19501fe5ac))
* added replacement of local node with warp node when specified in configuration ([44e1d3c](https://github.com/meetecho/juturna/commit/44e1d3cb9fe128df321c9a0a06c435fbe00e2b0a))
* adding the clear buffer function ([39b4a86](https://github.com/meetecho/juturna/commit/39b4a86fd2d074c63cf123d074dc9c8e371acde8))
* audio rtp av node output audio does not conform with original rtp audio node ([15b3b1d](https://github.com/meetecho/juturna/commit/15b3b1dcca11b13f1d266276389a5cd3c7facdaf))
* audio rtp av node output shape ([16538fe](https://github.com/meetecho/juturna/commit/16538fe1bfdc805f38436b290791ba9595c25c4c))
* **audio_rtp:** ([#25](https://github.com/meetecho/juturna/issues/25)) Infer the incoming audio channels by parsing the encoding_clock_channel parameter ([eace777](https://github.com/meetecho/juturna/commit/eace77729571388201ebc03fdb752f5465527990))
* **audio_rtp:** ([#30](https://github.com/meetecho/juturna/issues/30)) improve process lifecycle management and restart handling ([fa3ad80](https://github.com/meetecho/juturna/commit/fa3ad80d4ad904d5a0929248c555972c0768b2de))
* **audio_rtp:** ([#32](https://github.com/meetecho/juturna/issues/32)) enforcing integers to automatic port assignment ([1cf8e6f](https://github.com/meetecho/juturna/commit/1cf8e6f1f8ebebdcbd196479fa373db21610bfaf))
* **audio_rtp:** ([#32](https://github.com/meetecho/juturna/issues/32)) enforcing integers to automatic port assignment ([d7578e6](https://github.com/meetecho/juturna/commit/d7578e6b3e9228530d5df397ac03aed6c9b3af43))
* **audio_rtp:** removing timeout from monitor_thread join ([fcfe338](https://github.com/meetecho/juturna/commit/fcfe3389defda95eccb43fa397a762fbb442557b))
* **audio_rtp:** removing timeout from monitor_thread join in order to avoid deadlocks on exiting ([0bce3b9](https://github.com/meetecho/juturna/commit/0bce3b92bd0e23d185625def83773e8328fe0680))
* buffer check log becomes a debug log ([c6298da](https://github.com/meetecho/juturna/commit/c6298da49c9bd947d3cd3d5daca426ba05efd3fd))
* builded protos are now importable within the warp node and the remotizer utilities ([1f66d3c](https://github.com/meetecho/juturna/commit/1f66d3c0e68a76ffca76fb0d97a08299075aad17))
* changed import paths in remote service and corresponding test file to match the path produced by proto compilation script ([d589691](https://github.com/meetecho/juturna/commit/d5896914c622c5a4c0c2cafb00bb7544777b2e64))
* **core:** fixed serialization bug when a message carrying a batch is serialized, fixed serialization method for batch payloads, fixed bug in buffer consume function when a batch needs to be processed, e2e testing components added to test core functionalities ([dc103b2](https://github.com/meetecho/juturna/commit/dc103b26e8bd0856672534606b3eb8ce29309813))
* **docs:** remove outdated LIFO queue documentation ([e454778](https://github.com/meetecho/juturna/commit/e4547783a065de6095a8ebf315cfb77e68b02984))
* exporting JUTURNA_MAX_QUEUE_SIZE correctly ([89e1996](https://github.com/meetecho/juturna/commit/89e19967f2b9eea2e5a39b6913505e9ba1938d58))
* handle isolated nodes in DAG execution ([bc89519](https://github.com/meetecho/juturna/commit/bc89519885a7ad936fbeaca5ed6fed25ea6cffa3))
* JUTURNA_MAX_QUEUE_SIZE now is safe ([2539e6e](https://github.com/meetecho/juturna/commit/2539e6e3d5f961db3757f4b0df995b7b1dfc5b36))
* node.py's source thread termination must have a valid source_f ([a2ecea6](https://github.com/meetecho/juturna/commit/a2ecea6528acbefbdbbfbc4e6e3ec39ba23070cb))
* node.py's source thread termination must have a valid source_f ([40c3400](https://github.com/meetecho/juturna/commit/40c34009f368e987d186d782b164360d2d52bb09))
* **node:** output stuttering for videostream node ([31408ac](https://github.com/meetecho/juturna/commit/31408ace536cdbe1d857d129d9ab6b8d0abc85cd)), closes [#14](https://github.com/meetecho/juturna/issues/14)
* **notifier_udp:** udp packages now are chunked according to the header_size ([1416f48](https://github.com/meetecho/juturna/commit/1416f483a5d86fa543f109e4505f43d896d01add))
* now get_env_var receives a generic Type ([9aec61c](https://github.com/meetecho/juturna/commit/9aec61c5f5acf0140b1d6684221e82302b74da16))
* **payloads:** BasePayloads now handles deepcopy autonomously ([bd70f04](https://github.com/meetecho/juturna/commit/bd70f044ddc92f203f3513ca734ce6dc6fc45c4d))
* **payloads:** remove duplicate BasePayload import ([bbf33e4](https://github.com/meetecho/juturna/commit/bbf33e424bf197685d07b9738db5d4eb79e912ed))
* **payloads:** update juturna and prototype payloads ([75ec316](https://github.com/meetecho/juturna/commit/75ec31682455aeebb6ded81d5083f60f93bd4743))
* **payloads:** update the Payload class ([006c30d](https://github.com/meetecho/juturna/commit/006c30d9499b5470d6cd9b17a8773cb927d888f7))
* **payloads:** use base64 to serialize BytesPayload ([1a20350](https://github.com/meetecho/juturna/commit/1a20350f4c229ec8e063782c69244ba3c446b7a5))
* **proto:** change metadata proto type ([b7746bc](https://github.com/meetecho/juturna/commit/b7746bc94fe2fdb463636a097646b84b6082356b))
* **proto:** change metadata proto type ([c0ac892](https://github.com/meetecho/juturna/commit/c0ac892f373d8077438f7b8929b7152c1fcdce8a))
* reintroduced base payload in payload module to keep compatibility with newly created nodes ([ef941dd](https://github.com/meetecho/juturna/commit/ef941dd16e0fd386627b80337cba1270c4684283))
* **remotizer:** add a set of helpers to handle metadata serialization ([053ef12](https://github.com/meetecho/juturna/commit/053ef124d0b5757464c917fe44b12520bef7c632))
* **remotizer:** bytes serialization now relies on b64 encoding ([1b152cd](https://github.com/meetecho/juturna/commit/1b152cd16ee689b621015d24a8e477840ac5f9a9))
* **remotizer:** convert meta MappingProxyType to dict ([1f14bd1](https://github.com/meetecho/juturna/commit/1f14bd1656855f2bfb84fb18539ebcecfc54ab04))
* Remove default encoder from Node.dump_json method ([c96f052](https://github.com/meetecho/juturna/commit/c96f05213343705544d3bd2e9206ccdc172a7352))
* removing old starting approach (was already commented) ([12e48f3](https://github.com/meetecho/juturna/commit/12e48f3e29d5c1fba6b6da8172aadb880c7b9a66))
* removing stderr from subprocess in nodes/soruce/audio-rtp ([b915fb2](https://github.com/meetecho/juturna/commit/b915fb210eeb882a7ad0b74a5827ae6b8b728c27))
* replacing the LIFO queues with a FIFO to prevent misordering during burst ([8bfe611](https://github.com/meetecho/juturna/commit/8bfe6117b67934cdf4438ac32c21d96fb5feb994))
* restoring set_source insteaf of set_origin ([2e52fc9](https://github.com/meetecho/juturna/commit/2e52fc9103c9ae4d87ffdff4043509e27400215c))
* several minor fixes ([60e3b47](https://github.com/meetecho/juturna/commit/60e3b4738958be3159a2ced46dc998d348c68d84))
* solved pipe-node coupling by adding telemetry manager as defined in [#100](https://github.com/meetecho/juturna/issues/100) ([b3a2fdd](https://github.com/meetecho/juturna/commit/b3a2fdd93d8fbe83c99ad435bfe8b1b39f42a2b2))
* starting failure when no edges are declared in dag ([c4c8d1b](https://github.com/meetecho/juturna/commit/c4c8d1ba62c67582164729e08413a8c2d81e7e0e))
* telemetry manager now starts before nodes ([0b915cc](https://github.com/meetecho/juturna/commit/0b915cc6c57071e77c2900c96ac6a4653989543e))
* **transcriber_whispy:** derive start_abs from size and sequence_number ([f1cae64](https://github.com/meetecho/juturna/commit/f1cae64077c7bfaf30d5ebd900c1d4c6dacb6138))
* **transcriber_whispy:** derive start_abs from size and sequence_number ([d7e3089](https://github.com/meetecho/juturna/commit/d7e3089671ff6aadd8945f2c52d7e427c302edb1))
* **transcriber_whispy:** logging results ([03a1ef5](https://github.com/meetecho/juturna/commit/03a1ef5994849142e62727f3159d243d2a77f1f9))
* **transcriber_whispy:** logging results ([a031d4f](https://github.com/meetecho/juturna/commit/a031d4fd70b7a92793c318bb22ccc3d91201028e))
* **transcriber_whispy:** reverting start_abs fix using [@b3by](https://github.com/b3by)'s suggestions ([467ee55](https://github.com/meetecho/juturna/commit/467ee5518214b14b84199fee91bdfe4bacabed0f))
* **warp:** correct typos in warp files ([8cf3cb4](https://github.com/meetecho/juturna/commit/8cf3cb4850aa20dc130a94c7462b0f4a90c85388))
* **warp:** restore missing auto-generated proto file ([b0c840e](https://github.com/meetecho/juturna/commit/b0c840ef2698033dd1c034dcb09840c944d754bc))
* **yolo-detector:** avoid adding meta if no box has been detected ([44a00b8](https://github.com/meetecho/juturna/commit/44a00b8236e4e4b2a289557bc7850d7c71fa4cfb))
* **yolo-detector:** cleanup deleted parameter ([76a67c3](https://github.com/meetecho/juturna/commit/76a67c3b895a8bf6ae893aaa970ff8df509149ad))
* **yolo-detector:** expose the whole result in outgoing message ([7edc4dc](https://github.com/meetecho/juturna/commit/7edc4dca9a9e599e026e8c117614c23c46afc085))


### Documentation

* added documentation for warp nodes and remote service cli ([d79c33f](https://github.com/meetecho/juturna/commit/d79c33fa8ea5d4257d823cfb42cf54ee61445469))
* added entry in cli page for dependency aggregator ([db67b50](https://github.com/meetecho/juturna/commit/db67b5016a933ecf35609a077eca19aeda21fa75))
* added explanation for remote nodes and observability ([6574694](https://github.com/meetecho/juturna/commit/6574694959e1588fde7cd5880e9fdea0ee0a0b00))
* added paragraph about environment variables in configuration files ([b2c4322](https://github.com/meetecho/juturna/commit/b2c432206c7900f7231407575fd45968d5d8041e))
* added placeholder list of built in nodes ([b1ae066](https://github.com/meetecho/juturna/commit/b1ae066d98cb9d37b87c186239737bf42dad4d06))
* added tutorial for creating new pipes ([67d8a21](https://github.com/meetecho/juturna/commit/67d8a21fb6079bf72133bc2047c94a2c73f57e98))
* adding the meetecho icon ([782de3c](https://github.com/meetecho/juturna/commit/782de3c4e28827c8f5f5e7e855216a7282e51b45))
* bumping peaceiris/actions-gh-pages version to 4 ([c58f5cc](https://github.com/meetecho/juturna/commit/c58f5cc62f48627814852a6e1848f18ccc9bf0c5))
* **core:** fixed missing newline for message doc file ([25d0a97](https://github.com/meetecho/juturna/commit/25d0a9784b2eed968a190ed1da71cb635ac0793d))
* documentation expansion for nodes, messages, and pipelines ([c4984b5](https://github.com/meetecho/juturna/commit/c4984b59a5c5a55d1458fa923e4d27c6509ffc91))
* dried out readme file ([aca70c9](https://github.com/meetecho/juturna/commit/aca70c92d06df2d99231d65c0e4c4ee604ca8684))
* experimental using for custom.css ([2639cd4](https://github.com/meetecho/juturna/commit/2639cd4b8ec8382c1213d17f0edaab8378bb9ad2))
* fix typo on contributing page ([b1e1c2a](https://github.com/meetecho/juturna/commit/b1e1c2a3ed03c48d80545cccd98f4bceb9866045))
* improve the CONTRIBUTING.md page ([bc071c8](https://github.com/meetecho/juturna/commit/bc071c8ef324fd0874dd116642cad60ed664e813))
* more documentation added for entities, including messages, nodes, and pipelines ([c5f6fc5](https://github.com/meetecho/juturna/commit/c5f6fc5f294738abe21dd5b5ab4a087f28e9522e))
* navigation reorganized, added builder and publisher ([000bb6d](https://github.com/meetecho/juturna/commit/000bb6dd4a316e44209aa962c77e8d5618e41fb4))
* navigation reorganized, added builder and publisher ([b7a0834](https://github.com/meetecho/juturna/commit/b7a0834c519149127d6dc0defddea51e70f1d686))
* new section and pages for built-in nodes and apis ([c91bb38](https://github.com/meetecho/juturna/commit/c91bb3818440c17744b3d39ef61c7c54318c9ccf))
* removed outdated LIFO queue documentation ([8dade49](https://github.com/meetecho/juturna/commit/8dade49e7552da39e618651d42fca370e524e09f))
* removing duplicate custom css and disabling the remaining one, removing the ./ path in conf.py ([9b9cec2](https://github.com/meetecho/juturna/commit/9b9cec2da43d50b3756601587802f6d9a3b8487b))
* removing explicit nojekyll touch, adding options in workflow ([e469bfe](https://github.com/meetecho/juturna/commit/e469bfe8f354fbdb17b8a20225a1c643584256b7))
* reverting the no nojekyll touch removal ([a03f851](https://github.com/meetecho/juturna/commit/a03f851ff9ef647c3f6712024010578b48ba93e1))
* reverting the no nojekyll touch removal, adding options in workflow ([26dde66](https://github.com/meetecho/juturna/commit/26dde66adf0025fcad683f4963a655659c48cf8d))
* revised description to focus on FIFO rationale and correct formatting ([6a7b1bc](https://github.com/meetecho/juturna/commit/6a7b1bcdf0695da67527e1fec5c747005e5189b4))
* tutorial for custom node creation ([ea5f4b8](https://github.com/meetecho/juturna/commit/ea5f4b8ae77d2127bf80b1b5938b23d518c50d26))
* updating the README.md and writing the intial draft for CONTRIBUTING.md ([dc428de](https://github.com/meetecho/juturna/commit/dc428de9e7251751e2806f5d5deb145d7c1cf071))


### Miscellaneous Chores

* release 2.0.0 ([598594d](https://github.com/meetecho/juturna/commit/598594d639c47e58a93264c46918e1b50e6d8fe3))


### Code Refactoring

* change build files for protobuf compilation and fix warp node setup ([eb145a4](https://github.com/meetecho/juturna/commit/eb145a43917dfc7516a848795baa56566f1d14c0))
* entry point to spawn remotization service now moved into CLI commands ([b396665](https://github.com/meetecho/juturna/commit/b396665c35ce94897f23339d6187ff1f4192f701))
* major review of audio rtp ([30965c8](https://github.com/meetecho/juturna/commit/30965c8e5c76a08349c43f1f8b6b5ad22bc03484))
* **payloads:** removed useless import ([83bfc84](https://github.com/meetecho/juturna/commit/83bfc84f42f3cf5579cc216e9533a3e5b0654cd2))
* remotizer CLI now accepts file path for default config content ([1d1eb6a](https://github.com/meetecho/juturna/commit/1d1eb6a37d2061f3d8a3ce55a209a8c6ea697948))
* **remotizer:** cleanup sanitizer function ([0e1d382](https://github.com/meetecho/juturna/commit/0e1d3826e54ac3a512bbf85e2aecde97dc9feed4))
* **warp:** resolve several quality code issues ([97b8ce4](https://github.com/meetecho/juturna/commit/97b8ce462d1a2abc273cc654fdb53db81804606c))

## [Unreleased]



Releases up to version 1.0.2 were not tracked retroactively, so changelog entries start from subsequent versions
## [1.0.2] - 2025-11-27
