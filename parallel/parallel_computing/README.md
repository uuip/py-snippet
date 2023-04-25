1. python的multiprocessing默认是fork模式，完整复制父进程内存。

    `mp.set_start_method("spawn")`

2. worker执行的函数中包含connection、文件（log）handler时，应当要在子进程内初始化。

    - 数据库连接池：DBUtils 或者 参照redis连接池
3. Django与多进程：

   在3.x版本Django 默认配置CONN_MAX_AGE=0，每次查询后关闭。即使多进程，连接正常。

4. celery、Django与多进程：

   >(worker1)session1 读取数据  
   耗时操作...  
   (worker2)session2 修改数据，commit  
   session1 耗时操作完成，直接update或者save

- 一个表在同一时刻只有一个任务修改
- 行级锁：
  select_for_update and nowait
     ```
     with transaction.atomic():
             qs = Something.objects.select_for_update(nowait=True).filter(...)
     ```
     nowait默认值False，它等到锁时，select_for_update前语句获得的实效性数据或者判断可能过期
- 
     ```
     obj.refresh_from_db()  
     obj.save(update_fields=["some"])
     ```

5. celery的log

    celery的启动参数 -f some%n%I.log，如果是some.log，十有八九会触发竞争条件，不一定报错，后者把前者的覆盖，或者空文件。
    - Queue handler
    - concurrent_log_handler



