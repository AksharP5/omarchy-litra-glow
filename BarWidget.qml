import QtQuick
import qs.Commons
import qs.Ui

BarWidget {
  id: root
  moduleName: "akshar.litra-glow"

  readonly property var service: bar?.shell?.serviceFor(moduleName) ?? null
  readonly property bool connected: !!service && service.connected
  readonly property bool hovering: button.tooltipHovered || popup.containsMouse
    || brightnessRow.dragging || temperatureRow.dragging
  property bool popupOpen: false

  function close() { popupOpen = false }

  // A short delay keeps the card from flashing when the pointer crosses the
  // bar, and lets it cross the gap between the icon and the card.
  onHoveringChanged: {
    hoverDelay.interval = hovering ? 250 : 300
    hoverDelay.restart()
  }
  onConnectedChanged: if (!connected) close()

  Timer {
    id: hoverDelay
    onTriggered: root.popupOpen = root.hovering && root.connected
  }

  component SliderRow: Column {
    id: row

    property string label
    property string unit
    property alias minimum: slider.minimum
    property alias maximum: slider.maximum
    property alias value: slider.value
    property alias dragging: slider.dragging
    property alias step: slider.step
    // Temperature only exists in steps of 100 K.
    property int snap: 1
    readonly property int shown: Math.round(slider.liveValue / snap) * snap

    signal picked(int value)

    width: parent.width
    spacing: Style.space(2)

    Item {
      width: parent.width
      implicitHeight: header.implicitHeight

      PanelSectionHeader {
        id: header
        text: row.label
        foreground: root.bar.foreground
        fontFamily: root.bar.fontFamily
        anchors.left: parent.left
      }

      PanelSectionHeader {
        text: row.shown + " " + row.unit
        foreground: root.bar.foreground
        fontFamily: root.bar.fontFamily
        anchors.right: parent.right
      }
    }

    PanelSlider {
      id: slider
      bar: root.bar
      width: parent.width
      integer: true
      onMoved: row.picked(row.shown)
    }
  }

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: root.connected && root.service.powered ? "󰛨" : "󰌶"
    dimmed: !root.connected
    tooltipText: root.connected || !root.service || !root.service.ready ? ""
      : root.service.error || "Litra Glow not connected"
    onPressed: function(mouseButton) {
      if (root.connected && mouseButton === Qt.LeftButton) root.service.toggle()
    }
  }

  PopupCard {
    id: popup
    anchorItem: button
    bar: root.bar
    owner: root
    open: root.popupOpen
    triggerMode: "hover"
    contentWidth: popup.fittedContentWidth(Style.space(260))
    contentHeight: popup.fittedContentHeight(column.implicitHeight)

    Column {
      id: column
      anchors.fill: parent
      spacing: Style.space(6)

      SliderRow {
        id: brightnessRow
        label: "Brightness"
        unit: "lm"
        minimum: 20
        maximum: 250
        step: 10
        value: root.service ? root.service.brightness : minimum
        onPicked: function(lumens) { root.service.setBrightness(lumens) }
      }

      SliderRow {
        id: temperatureRow
        label: "Temperature"
        unit: "K"
        minimum: 2700
        maximum: 6500
        step: 100
        snap: 100
        value: root.service ? root.service.temperature : minimum
        onPicked: function(kelvin) { root.service.setTemperature(kelvin) }
      }
    }
  }
}
