"""RTP payload boundaries as specified in RFC 3550, sections 5.1 and 5.3.1."""

from struct import pack

import pytest

from juturna.utils.net_utils import RTPDatagram


def packet(csrcs=(), extension=None, payload=b'audio', padding=0):
    flags = 0x80 | len(csrcs)
    if extension is not None:
        flags |= 0x10
    if padding:
        flags |= 0x20
    data = pack('!BBHII', flags, 96, 123, 456, 789)
    data += b''.join(pack('!I', source) for source in csrcs)
    if extension is not None:
        data += pack('!HH', 0xBEDE, len(extension) // 4) + extension
    data += payload
    if padding:
        data += bytes(padding - 1) + bytes([padding])
    return data


@pytest.mark.parametrize('count', [0, 1, 3, 4, 15])
def test_csrcs_are_not_payload(count):
    sources = tuple(range(10, 10 + count))
    data = packet(csrcs=sources)
    parsed = RTPDatagram(data)
    assert parsed.csrs == [(source,) for source in sources]
    assert parsed.payload == b'audio'
    assert parsed.datagram == data


@pytest.mark.parametrize('csrcs', [(), (10, 20)])
@pytest.mark.parametrize('extension', [b'', b'\x01\x02\x03\x04', b'abcdefgh'])
def test_extension_length_is_in_words(csrcs, extension):
    parsed = RTPDatagram(packet(csrcs=csrcs, extension=extension))
    assert parsed.extension_header_id == 0xBEDE
    assert parsed.extension_header_len == len(extension) // 4
    assert parsed.extension_header == extension
    assert parsed.payload == b'audio'


@pytest.mark.parametrize('padding', [1, 4, 255])
def test_padding_is_not_payload(padding):
    parsed = RTPDatagram(
        packet(csrcs=(10,), extension=b'abcd', padding=padding)
    )
    assert parsed.payload == b'audio'


def test_replacing_datagram_clears_optional_headers():
    parsed = RTPDatagram(packet(csrcs=(10,), extension=b'abcd'))
    parsed.datagram = packet(csrcs=(20,))
    assert parsed.csrs == [(20,)]
    assert parsed.extension_header == b''
    assert parsed.extension_header_id == 0
    assert parsed.extension_header_len == 0
    assert parsed.payload == b'audio'


@pytest.mark.parametrize('padding', [0, 255])
def test_rejects_invalid_padding_count(padding):
    data = pack('!BBHII', 0xA0, 96, 123, 456, 789) + b'abc' + bytes([padding])
    with pytest.raises(ValueError, match='padding length'):
        RTPDatagram(data)
