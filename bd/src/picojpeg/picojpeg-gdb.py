import gdb
import numpy as np
import scipy as sp
from PIL import Image
import io
import json


class TimeFunction(gdb.Command):
    def __init__(self):
        super(TimeFunction, self).__init__("time-function", gdb.COMMAND_USER)

        self.stops = 0
        self.iters = 1
        self.emnist = sp.io.loadmat('bd/src/picojpeg/matlab/emnist-byclass.mat')

    def invoke(self, arg, from_tty):
        argv = gdb.string_to_argv(arg)
        if len(argv) == 3:
            self.iters = int(argv[0])
            fn = argv[1]
            opts = argv[2]
        else:
            print(argv)
            raise NameError("Usage: time-function iterations filename opts")
        gdb.write(f"Running for {self.iters} iteration{"s" if self.iters != 1 else ""}\n")

        bp = gdb.Breakpoint("stop_trigger")
        bp.silent = True


        rng = np.random.default_rng(seed=3141592653)

        times = [0] * self.iters

        def stop_handler(event):
            if isinstance(event, gdb.BreakpointEvent):
                try:
                    duration = gdb.parse_and_eval("*0xe0001004")
                except e:
                    return
                times[self.stops] = int(duration)

                #imraw = (rng.normal(128, 21, (64, 51)))
                imraw = np.reshape(self.emnist['dataset'][0][0][0][0][0][0][self.stops], (28, 28))
                im = Image.fromarray(imraw, mode='L')
                b = io.BytesIO()
                im.save(b, 'JPEG', quality=95)
                b.seek(0)
                jpeg_data = gdb.parse_and_eval("jpeg_data")
                jpeg_data.bytes = b.read().ljust(4096, b'\0')

                self.stops += 1

        self.stops = 0
        gdb.events.stop.connect(stop_handler)
        while self.stops < self.iters:
            gdb.execute("continue")
        gdb.events.stop.disconnect(stop_handler)
        if self.iters <= 500:
            gdb.write(f"duration: {times}\n")
        with open(fn, "w") as f:
            f.write(json.dumps({"t": times, "opts": opts.split("_")}))

        bp.delete()


TimeFunction()
