package app

import android.app.Application

/** The shipped app's composition root: services that live as long as the process, built once (not per Activity,
 * which rotation recreates). Real services only. */
class StarterApp : Application()
