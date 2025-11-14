
import java.net.Socket
plugins {

}

group = "org.example"
version = "1.0-SNAPSHOT"

repositories {
    mavenCentral()
}




val pyDir = layout.projectDirectory.dir("src")
val flaskServer = pyDir.file("CAServer.py").asFile

val os = org.gradle.internal.os.OperatingSystem.current()
val pyCmd = if (os.isWindows) "python" else "python3"

val localRoot = layout.projectDirectory

//Venv stuff
val venvPy = if (os.isWindows) {
    localRoot.file("venv/Scripts/python.exe").asFile
} else {
    localRoot.file("venv/bin/python").asFile
}



val pipPath = if (os.isWindows) {
    localRoot.file("venv/Scripts/pip.exe").asFile
} else {
    localRoot.file("venv/bin/pip").asFile
}



val logsDir = localRoot.dir("logs").asFile
val pidFile = logsDir.resolve("logs.pid")




tasks.register<Exec>("setUpVenv") {
    workingDir = localRoot.asFile
    dependsOn("nukeVenv") // while testing
    doFirst {
        println("Setting up venv for: $os")
        if (venvPy.exists()) {
            println("Venv already exists - exiting task")
            throw StopExecutionException()
        } else {
            println("Setting up the venv")
        }
    }

    commandLine(pyCmd, "-m", "venv", "venv")
}

tasks.register<Exec>("upgradePip") {

    dependsOn("setUpVenv")
    commandLine(
        venvPy.absolutePath, "-m", "pip", "install", "--upgrade",
        "pip", "setuptools", "wheel"
    )
}

tasks.register<Exec>("installVenvDependencies") {
    dependsOn("upgradePip")

    workingDir = pyDir.asFile

    doFirst {
        val deps = pyDir.file("requirements.txt").asFile
        if (!deps.exists()) {
            println("Missing requirements.txt in PythonTest - exiting installs")
            throw org.gradle.api.tasks.StopExecutionException()
        } else {
            println("Installing dependencies...")

            if (!pipPath.exists()) {
                throw org.gradle.api.GradleException("Pip not found in venv: $pipPath")
            }

            commandLine(pipPath.absolutePath, "install", "-r", "requirements.txt")
        }
    }
}

tasks.register("flaskRun") {
    group = "flask"
    description = "Run Flask server in background"

    dependsOn("installVenvDependencies")

    doLast {

        if (!venvPy.exists()) error("Missing venv: $venvPy")
        if (!flaskServer.exists()) error("Missing CAServer.py")

        logsDir.mkdirs()
        val outFile = logsDir.resolve("flask.out")
        val errFile = logsDir.resolve("flask.err")

        val cmd = listOf(venvPy.absolutePath, "CAServer.py")
        val pb = ProcessBuilder(cmd)
            .directory(pyDir.asFile)
            .redirectOutput(outFile)
            .redirectError(errFile)//For some reason - post requests are going in here
        pb.environment().putIfAbsent("PYTHONUNBUFFERED", "1")

        val proc = pb.start()
        pidFile.writeText(proc.pid().toString())

        println("Flask started detached (PID=${proc.pid()})")
    }
}


//Helper tasks
tasks.register("flaskStatus") {

    doLast {
        if(!pidFile.exists()) {
            println("No PID file exists - flask server not running?")
            return@doLast
        }
        val pidText = pidFile.readText().trim()
        val pid = pidText.toLongOrNull()

        if(pid == null) {
            println("Bad PID file contents: ${pidText}")
            return@doLast
        }

        try {
            val handle = ProcessHandle.of(pid)
            if(handle.isPresent && handle.get().isAlive) {
                println("Flask is running with PID ${pid}")
            }
            else {
                println("pid file exists, but the process is not alive")
            }
        }
        catch (t: Throwable) {
            println("Could not check flask status ${t.message}")
        }
    }
}

tasks.register("flaskStop") {
    doLast {
        if (!pidFile.exists()) {
            println("No PID file. Nothing to stop.")
            return@doLast
        }
        val pid = pidFile.readText().trim()
        try {
            if (os.isWindows) {
                exec { commandLine("cmd", "/c", "taskkill", "/PID", pid, "/T", "/F") }
            } else {
                exec { commandLine("bash", "-lc", "kill -TERM $pid || true") }
            }
            println("Sent stop signal to PID=$pid")
        } finally {
            pidFile.delete()
        }
    }
}

tasks.register("waitForFlask") {
    group = "infra"
    description = "Wait until Flask is listening on 127.0.0.1:5000"
    dependsOn("flaskRun")
    doLast {
        val host = "127.0.0.1"
        val port = 5000
        val deadline = System.currentTimeMillis() + 60_000
        var tries = 0

        println("Waiting for Flask to start on $host:$port …")

        while (System.currentTimeMillis() < deadline) {
            try {
                Socket(host, port).use {
                    println("✔ Flask is ready after $tries attempts!")
                    return@doLast
                }
            } catch (e: Exception) {
                tries++
                println("Attempt $tries: Flask not ready yet (${e::class.simpleName})")
                Thread.sleep(500)
            }
        }

        throw RuntimeException("❌ Timed out after 60 seconds waiting for Flask")
    }
}


tasks.register("nukeVenv") {

    val venvDir = localRoot.dir("venv")


    doFirst {
        //Checking if the client already has a venv
        if (!venvDir.asFile.exists()) {
            println("No venv found at ${venvDir.asFile}. Skipping deletion.")
            return@doFirst
        }
        //if not, we detect the os they are on, and run different commands based on windows or unix. we need to change permissions, then delete the dir and its contents
        println("Preparing to delete venv at ${venvDir.asFile}")

        if (os.isWindows) {
            println("Detected Windows — clearing read-only attributes.")
            exec {
                commandLine("powershell", "-Command",
                    "attrib -r /s /d \"${venvDir.asFile}\\*\"; " +
                            "Remove-Item -Recurse -Force \"${venvDir.asFile}\"")
            }
        } else {
            println("Detected Unix-like OS — fixing permissions and deleting.")
            exec {
                commandLine("chmod", "-R", "u+w", venvDir.asFile.absolutePath)
            }
            delete(venvDir)
        }
    }
}


// certificateService/build.gradle.kts




/*
tasks.register<Exec>("runFlask") {

    dependsOn("installVenvDependencies")

    workingDir = pyDir.asFile

    println("Detected OS: $os")

    doFirst {
        if (!venvPy.exists()) {
            throw org.gradle.api.GradleException(
                "Missing venv interpreter at $venvPy. " +
                        "Create it: `python3 -m venv ${pyDir.asFile}/venv`"
            )
        }

        val flaskFile = pyDir.file("CAServer.py").asFile
        if (!flaskFile.exists()) {
            throw org.gradle.api.GradleException("CAServer.py not found in ${pyDir.asFile}")
        }

        println("Using interpreter: $venvPy")
    }

    // Either run via Flask CLI:
    // commandLine(venvPy.absolutePath, "-m", "flask", "--app", "flaskTest", "run",
    //     "--host", "127.0.0.1", "--port", "5000")

    // Or run the script directly (if you have `if __name__ == '__main__': app.run(...)`)
    commandLine(venvPy.absolutePath, "CAServer.py")
}
*/
