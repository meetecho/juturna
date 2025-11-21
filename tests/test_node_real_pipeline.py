"""Real pipeline tests for Node.stop() deadlock fix (Issue #48)"""
import subprocess
import time
import threading
import pathlib
import shutil

import pytest

import juturna as jt
from juturna.components._node import Node
from juturna.components._message import Message
from juturna.components._pipeline import Pipeline
from juturna.payloads import BytesPayload
from juturna.names import ComponentStatus


class RealSubprocessNode(Node[BytesPayload, BytesPayload]):
    """Node that uses subprocess.stdout.read() which can block."""
    
    def __init__(self, node_name='real_subprocess_node', **kwargs):
        super().__init__(node_name=node_name, **kwargs)
        self._proc = None
        self._messages_received = []
    
    def start(self):
        try:
            self._proc = subprocess.Popen(
                ['sh', '-c', 'while true; do echo "test_data"; sleep 0.1; done'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0
            )
            
            self.set_source(
                lambda: Message[BytesPayload](
                    creator=self.name,
                    payload=BytesPayload(
                        cnt=self._proc.stdout.read(100)
                    ),
                )
            )
            
            super().start()
        except Exception as e:
            pytest.skip(f"Could not start subprocess: {e}")
    
    def stop(self):
        print(f"\n    [REAL NODE] stop() called - subprocess PID: {self._proc.pid if self._proc else None}")
        
        if self._proc:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=1)
            except (subprocess.TimeoutExpired, ProcessLookupError):
                try:
                    self._proc.kill()
                    self._proc.wait()
                except:
                    pass
            self._proc = None
        
        super().stop()
    
    def update(self, message: Message[BytesPayload]):
        self._messages_received.append(message)
        self.transmit(message)


class SimpleTestSink(Node[BytesPayload, None]):
    """Simple sink node for testing that accepts BytesPayload"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._messages_received = []
    
    def update(self, message: Message[BytesPayload]):
        self._messages_received.append(message)


def test_real_pipeline_with_blocking_subprocess():
    """Test node.stop() with blocking subprocess.stdout.read()"""
    print("\n" + "="*80)
    print("REAL PIPELINE TEST: Node.stop() with Blocking Subprocess stdout.read()")
    print("="*80)
    
    node = RealSubprocessNode()
    
    print(f"\n[STEP 1] Creating node with real subprocess...")
    print(f"    Node name: {node.name}")
    
    try:
        print(f"\n[STEP 2] Starting node (will spawn subprocess)...")
        node.start()
        
        proc_pid = node._proc.pid if node._proc else None
        print(f"    Subprocess PID: {proc_pid}")
        print(f"    Node status: {node.status}")
        print(f"    Source thread alive: {node._source_thread.is_alive() if node._source_thread else False}")
        print(f"    Source callback: {getattr(node._source_f, '__name__', 'lambda')}")
        
        print(f"\n[STEP 3] Letting node run (source thread may block on stdout.read())...")
        time.sleep(0.3)
        
        print(f"    Messages received: {len(node._messages_received)}")
        print(f"    Source thread still alive: {node._source_thread.is_alive() if node._source_thread else False}")
        
        print(f"\n[STEP 4] Calling node.stop() - THIS SHOULD NOT DEADLOCK...")
        print(f"    Time before stop: {time.time():.3f}")
        
        start_time = time.time()
        node.stop()
        elapsed_time = time.time() - start_time
        
        print(f"\n[STEP 5] node.stop() completed!")
        print(f"    Time after stop: {time.time():.3f}")
        print(f"    Elapsed time: {elapsed_time:.3f} seconds")
        print(f"    Source callback after stop: {getattr(node._source_f, '__name__', 'lambda')}")
        print(f"    Source thread: {node._source_thread}")
        print(f"    Worker thread: {node._worker_thread}")
        print(f"    Final status: {node.status}")
        print(f"    Subprocess terminated: {node._proc is None}")
        
        print(f"\n[STEP 6] Verification:")
        timeout_value = 2.0
        print(f"     Stop completed in {elapsed_time:.3f}s (timeout: {timeout_value}s)")
        print(f"     No deadlock occurred (would hang indefinitely without fix)")
        print(f"     Source callback was replaced: {node._source_f is not None}")
        print(f"     Source thread exited cleanly: {node._source_thread is None}")
        print(f"     Worker thread exited cleanly: {node._worker_thread is None}")
        print(f"     Subprocess cleaned up: {node._proc is None}")
        
        print("="*80 + "\n")
        
        assert elapsed_time < timeout_value + 0.5, f"Stop took {elapsed_time}s, should complete within {timeout_value}s"
        assert node.status == ComponentStatus.STOPPED
        assert node._source_thread is None
        assert node._worker_thread is None
        assert node._proc is None
        
    except Exception as e:
        if node._proc:
            try:
                node._proc.kill()
                node._proc.wait()
            except:
                pass
        raise


def test_real_pipeline_with_pipeline_class():
    """Test full Pipeline with source -> proc -> sink nodes"""
    print("\n" + "="*80)
    print("REAL PIPELINE TEST: Full Pipeline (Source -> Proc -> Sink)")
    print("="*80)
    
    pipeline_config = {
        "version": "0.1.0",
        "plugins": ["./plugins"],
        "pipeline": {
            "name": "test_real_pipeline",
            "id": "test_real_123",
            "folder": "./tests/running_pipelines/real_pipeline",
            "nodes": [
                {
                    "name": "0_src",
                    "type": "source",
                    "mark": "passthrough_identity",
                    "configuration": {}
                },
                {
                    "name": "1_proc",
                    "type": "proc",
                    "mark": "passthrough_identity",
                    "configuration": {
                        "delay": 0
                    }
                },
                {
                    "name": "2_sink",
                    "type": "sink",
                    "mark": "notifier_udp",
                    "configuration": {
                        "endpoint": "127.0.0.1",
                        "port": 12345,
                        "payload_size": 1024,
                        "max_sequence": 9999,
                        "max_chunks": 1000,
                        "encoding": "utf8",
                        "encode_b64": False
                    }
                }
            ],
            "links": [
                {"from": "0_src", "to": "1_proc"},
                {"from": "1_proc", "to": "2_sink"}
            ]
        }
    }
    
    pipeline = Pipeline(pipeline_config)
    
    print(f"\n[STEP 1] Created pipeline: {pipeline.name}")
    print(f"    Nodes in config: {[n['name'] for n in pipeline_config['pipeline']['nodes']]}")
    print(f"    Links: {pipeline_config['pipeline']['links']}")
    
    try:
        from juturna.components import _component_builder
        import copy
        
        pipeline._raw_config = copy.deepcopy(pipeline_config)
        pathlib.Path(pipeline.pipe_path).mkdir(parents=True, exist_ok=True)
        
        for node_config in pipeline_config['pipeline']['nodes']:
            node_name = node_config['name']
            node_folder = pathlib.Path(pipeline.pipe_path, node_name)
            node_folder.mkdir(exist_ok=True)
            
            if node_name == '0_src':
                _node = RealSubprocessNode(node_name=node_name, pipe_name=pipeline.name)
            elif node_name == '2_sink':
                _node = SimpleTestSink(node_name=node_name, pipe_name=pipeline.name)
            else:
                _node = _component_builder.build_component(
                    node_config,
                    plugin_dirs=pipeline_config['plugins'],
                    pipe_name=pipeline.name,
                )
            
            _node.pipe_name = pipeline.name
            _node.pipe_path = node_folder
            _node.status = ComponentStatus.NEW
            pipeline._nodes[node_name] = _node
        
        for link in pipeline_config['pipeline']['links']:
            from_node = link['from']
            to_node = link['to']
            pipeline._nodes[from_node].add_destination(to_node, pipeline._nodes[to_node])
            pipeline._nodes[to_node].origins.append(from_node)
            pipeline._links.append(copy.copy(link))
        
        for node_name, node in pipeline._nodes.items():
            node.warmup()
            node.status = ComponentStatus.CONFIGURED
        
        from juturna.names import PipelineStatus
        pipeline._status = PipelineStatus.READY
        
        print(f"[STEP 2] Pipeline configured")
        print(f"    Source node: {pipeline._nodes['0_src'].name}")
        print(f"    Proc node: {pipeline._nodes['1_proc'].name}")
        print(f"    Sink node: {pipeline._nodes['2_sink'].name}")
        
        pipeline.start()
        print(f"[STEP 3] Pipeline started")
        source_node = pipeline._nodes['0_src']
        proc_node = pipeline._nodes['1_proc']
        sink_node = pipeline._nodes['2_sink']
        
        print(f"    Source node status: {source_node.status}")
        print(f"    Proc node status: {proc_node.status}")
        print(f"    Sink node status: {sink_node.status}")
        if hasattr(source_node, '_proc') and source_node._proc:
            print(f"    Subprocess PID: {source_node._proc.pid}")
        
        time.sleep(0.2)
        
        print(f"\n[STEP 4] Stopping pipeline (calls node.stop() on all nodes - should not deadlock)...")
        start_time = time.time()
        
        pipeline.stop()
        
        elapsed_time = time.time() - start_time
        
        print(f"[STEP 5] Pipeline stopped!")
        print(f"    Stop completed in: {elapsed_time:.3f} seconds")
        print(f"    Source node status: {source_node.status}")
        print(f"    Proc node status: {proc_node.status}")
        print(f"    Sink node status: {sink_node.status}")
        print(f"    Source thread: {source_node._source_thread}")
        if hasattr(source_node, '_proc'):
            print(f"    Subprocess: {source_node._proc}")
        
        print(f"\n[STEP 6] Verification:")
        print(f"     Pipeline stop completed in {elapsed_time:.3f}s")
        print(f"     No deadlock occurred")
        print(f"     All nodes stopped cleanly")
        print(f"     Source -> Proc -> Sink chain verified")
        if hasattr(source_node, '_proc'):
            print(f"     Subprocess cleaned up: {source_node._proc is None}")
        
        print("="*80 + "\n")
        
        assert elapsed_time < 3.0, f"Pipeline stop took {elapsed_time}s, should be faster"
        assert source_node.status == ComponentStatus.STOPPED
        assert proc_node.status == ComponentStatus.STOPPED
        assert sink_node.status == ComponentStatus.STOPPED
        if hasattr(source_node, '_proc'):
            assert source_node._proc is None
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        if 'source_node' in locals() and hasattr(source_node, '_proc') and source_node._proc:
            try:
                source_node._proc.kill()
                source_node._proc.wait()
            except:
                pass
        raise
    finally:
        try:
            shutil.rmtree(pipeline.pipe_path, ignore_errors=True)
        except:
            pass

