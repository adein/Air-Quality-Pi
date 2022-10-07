import signal


class GracefulKiller:
    kill_now = False
    aq = None

    def __init__(self, air_quality):
        self.aq = air_quality
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, signum, frame):
        print('Stopping...')
        if self.aq is not None:
            self.aq.stop()
        self.kill_now = True
        print('Stopped.')


if __name__ == '__main__':
    import AirQuality

    print('Starting...')
    aq = AirQuality.AirQuality()
    killer = GracefulKiller(aq)
    print('Started')

    print('Initializing sensors')
    aq.start(60, 5)
