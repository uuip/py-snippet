job = group(
    traverse.s(rpc_url, block_num, extra_data)
    for block_num in range(start_block, min(latest_block_num + 1, start_block + 10))
)
chord(job, chain_info_callback.s()).apply_async()
