Policy
------

- Outputs whose hash or key field is data rather than a hash or key now count
  as data carrier bytes, so under the default settings a transaction carrying
  them is rejected with `txn-datacarrier-nonstandard`. This covers taproot outputs
  whose key is not on the curve, and any hash with one byte value repeated
  eight times or six times in a row, past up to seven leading zero bytes.
  Lightning anchor outputs, ordinals postage, vanity addresses whose hash
  starts with up to seven zero bytes and outputs to the all-zero burn hash are
  unaffected (the all-zero taproot key too). The new
  `-rejectfakeoutputs` option (default: 1, reset by `-corepolicy`) turns the
  detection off without accepting other non-standard data carriers.
- Payloads spread over three or more distinct P2WSH outputs that share one
  value of 546 sat or less (the OLGA layout, whatever magic it uses) are also
  data with the new `-datacarrierdustruns` option, which is off by default: a
  Lightning commitment with three or more equal in-flight HTLCs has the same
  layout, and refusing it could block a force close.
- The new `-fakeoutputtext` option (default: 1, reset by `-corepolicy`) also
  counts an output whose hash or key is all printable text as data, such as
  JSON token messages hidden in P2WSH programs.
- The new `-datacarrierdroppeditems` option (default: 1, reset by
  `-corepolicy`) counts items of a spent stack that the script removes without
  reading them (`OP_DROP`, `OP_2DROP`, `OP_NIP`) as data carrier bytes, so a
  spend that carries data in items its script throws away is rejected with
  `txn-datacarrier-nonstandard`. Items the script reads, such as signatures
  and hash preimages, are not counted.
