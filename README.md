# microtune: a tuning app supporting arbitrary tuning systems

microtune is essentially a guitar tuner--albeit a fairly advanced one. It was designed to tune instruments to any tuning system or pitch standard.

## Techincal details

The fundamental frequency estimator at the core of this tuner is based on [YIN](https://www.researchgate.net/publication/11367890_YIN_A_fundamental_frequency_estimator_for_speech_and_music), an efficient autocorrelation-based method. However, as I was developing this project, I discovered certain shortcomings and ways that I could improve the stability of the algorithm, especially for plucked instruments. For example, YIN often produces a "too low" error in which the estimated frequency is one or more octaves below the actual fundamental. I've implemented a regime in which estimates taken from shortly after a note is plucked--a time frame in which too-low estimates don't really happen--are used to correct for too-low error that often occur later as the note decays. This greatly improves the stability of plain YIN. Keep in mind that this is an optimization for plucked instruments, though the tuner also does well with sustained instruments, such as voice.

Secondly, the fundamental frequency estimate is not a point estimate, but rather uses the collection of rolling estimates to estimate the fundamental. This provides a smoother estimate of the fundamental frequency, and it also allows the user to visualize the spread/distribution of estimates. This can be useful to visualize since one can essentially see the confidence of the estimate which changes as the note decays.

As for alternate tuning systems, this repo comes with twelve-tone equal temperament, but the user can create any tuning system and drop it as a JSON file into the `resources/scales` directory. The format is simple: provide pairs of note number (i.e., scale degree) and cent values, where cent values range from 0 to 12000. Look at `EDO12.json` for an example. The pitch standard can also be adjusted on the fly so you can tune to, say, A = 430 Hz.

** Usage

The GUI can be run with varying levels of information exposed to the user. The minimal inferface looks like this:

picture of GUI

Yes, it's ugly. The full version looks like this:

picture of full GUI

Fields/parameters can just be left at default values. They're still around from when I was prototyping the algorithm, but you might find them interesting or useful.
