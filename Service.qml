import QtQuick
import Quickshell
import Quickshell.Io

Item {
  id: root

  property var shell: null
  property bool ready: false
  property bool connected: false
  property bool powered: false
  property int brightness: 250
  property int temperature: 6500
  property string error: ""

  readonly property string helperPath: decodeURIComponent(
    Qt.resolvedUrl("litra.py").toString().replace(/^file:\/\//, ""))

  function send(command) {
    if (helper.running) helper.write(command + "\n")
  }

  function toggle() { send("power toggle") }

  // Set the slider's value now so it does not jump back while the light
  // answers; the helper's reply replaces it with what the light reports.
  function setBrightness(lumens) {
    brightness = Math.round(lumens)
    send("brightness " + brightness)
  }

  function setTemperature(kelvin) {
    temperature = Math.round(kelvin / 100) * 100
    send("temperature " + temperature)
  }

  function apply(line) {
    try {
      var status = JSON.parse(line)
      root.connected = status.connected
      root.error = status.error
      if (status.connected) {
        root.powered = status.on
        root.brightness = status.brightness
        root.temperature = status.temperature
      }
    } catch (error) {
      root.error = "Cannot read Litra Glow status: " + error
    }
    root.ready = true
  }

  // One long-running helper reads the light every two seconds, so changes made
  // with the light's own buttons show up, and takes commands on stdin.
  Process {
    id: helper
    command: ["python3", root.helperPath, "watch"]
    running: true
    stdinEnabled: true
    stdout: SplitParser { onRead: function(line) { root.apply(line) } }
    stderr: StdioCollector { id: errors }
    onExited: function(exitCode) {
      root.ready = true
      root.connected = false
      root.error = errors.text.trim() || "Litra helper exited with code " + exitCode + "."
      restart.start()
    }
  }

  Timer {
    id: restart
    interval: 5000
    onTriggered: helper.running = true
  }

  IpcHandler {
    target: "akshar.litra-glow"
    function toggle(): void { root.toggle() }
    function brightness(lumens: int): void { root.setBrightness(lumens) }
    function temperature(kelvin: int): void { root.setTemperature(kelvin) }
    function status(): string {
      return JSON.stringify({
        connected: root.connected, on: root.powered, brightness: root.brightness,
        temperature: root.temperature, error: root.error
      })
    }
  }
}
