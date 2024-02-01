# microtune: a tuning app supporting arbitrary tuning systems

microtune can be used to estimate the fundamental frequency of sounds and accurately tune instruments according to any tuning system or pitch standard. The pitch (or fundamental frequency) estimator is based on [YIN](https://www.researchgate.net/publication/11367890_YIN_A_fundamental_frequency_estimator_for_speech_and_music), an autocorrelation-based method, but has been adapted and optimized to improve the the stability of the estimate. The app also allows you to visualize the confidence of the estimate as a probability density curve.

The GUI can be run with varying levels of information exposed to the user. The minimal inferface looks like this:

picture of GUI

Yes, it's ugly. The full version looks like this:

picture of full GUI

Fields/parameters can just be left at default values. They're still around from when I was prototyping the algorithm.
