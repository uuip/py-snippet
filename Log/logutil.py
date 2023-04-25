# coding=utf-8
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from logging.handlers import TimedRotatingFileHandler, RotatingFileHandler
from pathlib import Path


class TimedSizedRotatingFileHandler(TimedRotatingFileHandler):
    def __init__(
        self,
        filename,
        maxBytes=10 * 1024 * 1024,
        backupCount=20,
        when="d",
        encoding="utf-8",
    ):
        # backupCount=10,一共有11个log
        super().__init__(filename, when, 1, backupCount, encoding)
        self.maxBytes = maxBytes

    def sortfiles(self, filename):
        # name.log.2021-09-17_14-18-57.7  .1.2是新的，.9是旧的
        d, n = filename.split(".")[-2:]
        return d, -int(n)

    def getFilesToDelete(self):
        dirName, baseName = os.path.split(self.baseFilename)
        fileNames = os.listdir(dirName)
        result = []
        prefix = baseName + "."
        plen = len(prefix)
        for fileName in fileNames:
            if fileName[:plen] == prefix:
                suffix = fileName[plen:]
                if self.extMatch.match(suffix):
                    result.append(os.path.join(dirName, fileName))
        if len(result) < self.backupCount:
            result = []
        else:
            # 修改父类，添加排序方法
            result.sort(key=self.sortfiles)
            result = result[: len(result) - self.backupCount]
        return result

    def doRollover(self):
        """
        do a rollover; in this case, a date/time stamp is appended to the filename
        when the rollover happens.  However, you want the file to be named for the
        start of the interval, not the current time.  If there is a backup count,
        then we have to get a list of matching filenames, sort them and remove
        the one with the oldest suffix.
        """
        if self.stream:
            self.stream.close()
            self.stream = None
        # get the time that this sequence started at and make it a TimeTuple
        currentTime = int(time.time())
        dstNow = time.localtime(currentTime)[-1]
        t = self.rolloverAt - self.interval
        if self.utc:
            timeTuple = time.gmtime(t)
        else:
            timeTuple = time.localtime(t)
            dstThen = timeTuple[-1]
            if dstNow != dstThen:
                if dstNow:
                    addend = 3600
                else:
                    addend = -3600
                timeTuple = time.localtime(t + addend)
        # 修改变量名为dfnt, 使用RotatingFileHandlerdfnt.doRollover对dfn赋值，而这个是文件名模版
        # 形如 logs/name.log.2021-09-17_13-05-30
        dfnt = self.rotation_filename(
            self.baseFilename + "." + time.strftime(self.suffix, timeTuple)
        )
        ########上文来自TimedRotatingFileHandler.doRollover###############
        ########下文来自RotatingFileHandlerdfnt.doRollover###############
        if self.backupCount > 0:
            # log.9->log.10...log.2->log.1
            for i in range(self.backupCount - 1, 0, -1):
                # 修改了RotatingFileHandler.doRollover的下述两行
                sfn = self.rotation_filename("%s.%d" % (dfnt, i))
                dfn = self.rotation_filename("%s.%d" % (dfnt, i + 1))
                if os.path.exists(sfn):
                    if os.path.exists(dfn):
                        os.remove(dfn)
                    os.rename(sfn, dfn)
            # log->log.1 修改了RotatingFileHandler
            dfn = self.rotation_filename(dfnt + ".1")
            if os.path.exists(dfn):
                os.remove(dfn)
            self.rotate(self.baseFilename, dfn)
            # 下面2行来自TimedRotatingFileHandler.doRollover
            for s in self.getFilesToDelete():
                os.remove(s)
        ########下文来自TimedRotatingFileHandler.doRollover###############
        if not self.delay:
            self.stream = self._open()
        newRolloverAt = self.computeRollover(currentTime)
        while newRolloverAt <= currentTime:
            newRolloverAt = newRolloverAt + self.interval
        # If DST changes and midnight or weekly rollover, adjust for this.
        if (self.when == "MIDNIGHT" or self.when.startswith("W")) and not self.utc:
            dstAtRollover = time.localtime(newRolloverAt)[-1]
            if dstNow != dstAtRollover:
                if not dstNow:  # DST kicks in before next rollover, so we need to deduct an hour
                    addend = -3600
                else:  # DST bows out before next rollover, so we need to add an hour
                    addend = 3600
                newRolloverAt += addend
        self.rolloverAt = newRolloverAt

    def shouldRollover(self, record):
        bytime = TimedRotatingFileHandler.shouldRollover(self, record)
        bysize = RotatingFileHandler.shouldRollover(self, record)
        return bysize or bytime


def bj(secs):
    bj = timezone(timedelta(hours=+8))
    return datetime.fromtimestamp(secs, tz=bj).timetuple()


def getlogger(name="root", level="DEBUG", logdir=None):
    """
    每次用log都tm的太麻烦
    :param name: log名
    :param level: ['CRITICAL', 'FATAL', 'ERROR', 'WARN','INFO', 'DEBUG', 'NOTSET']
    :param logdir: 代码所在路径"."
    :return:
    """
    if isinstance(level, int):
        pass
    elif str(level) == level:
        level = level.upper()
    else:
        raise TypeError("Level not an integer or a valid string: %r" % level)
    log = logging.getLogger(name)
    log.setLevel(level)
    log.propagate = False
    if log.level == logging.DEBUG:
        sh = logging.StreamHandler()
        # time模块不支持格式化毫秒, 用 %(msecs)d 字段表示毫秒而不在datefmt指定
        # https://docs.python.org/zh-cn/3/library/logging.html#logrecord-attributes

        fmt = logging.Formatter(
            "[%(asctime)s %(lineno)3s %(levelname)s] %(message)s",
            datefmt="%m-%d %H:%M:%S",
        )
        fmt.converter = bj
        sh.setFormatter(fmt)
        log.addHandler(sh)
    if logdir:
        logdir = Path(logdir)
        if logdir.name not in {"log", "logs"}:
            logdir = Path(logdir) / "logs"
        if not logdir.exists():
            logdir.mkdir(parents=True, exist_ok=True)
        handler = TimedSizedRotatingFileHandler(str(logdir / (name + ".log")))
        fmt = logging.Formatter("[%(asctime)s %(module)s:%(lineno)3s %(levelname)s] %(message)s")
        fmt.converter = bj
        handler.setFormatter(fmt)
        handler.setLevel(max(log.level, logging.INFO))
        log.addHandler(handler)
    return log
