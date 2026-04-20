# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
