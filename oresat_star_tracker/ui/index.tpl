<!DOCTYPE html>
<html lang="en">
  <head>
    <title>OreSat Star Tracker {{version}}</title>
  </head>
  <body>
    <style>
      table {
        font-family: arial, sans-serif;
        border-collapse: collapse;
        margin-left: auto;
        margin-right: auto;
        width: 80%;
      }
      td, th {
        border: 1px solid #dddddd;
        text-align: left;
        padding: 8px;
        width: 50%;
      }
      #header {
        text-align: center;
      }
      #grid {
        text-align: center;
        display: grid;
        grid-template-columns: 25% 50% 25%;
      }
      #gridColum {
        text-align: center;
      }
      #image {
        width: 90%;
      }
    </style>
    <div id="header">
      <h2>OreSat Star Tracker {{version}}</h2>
    </div>
    <div id="grid">
      <div id="gridColumn">
        <!--only here for spacing-->
      </div>
      <div id="gridColumn">
        <!--the "//:0" is a basically the way to make any empty img-->
        <img id="image" src="//:0" alt="capture"/>
        <br/>
        <button onclick="downloadDisplayImage()">Download Display Image</button>
      </div>
      <div id="gridColumn">
        <h4>State Machine</h4>
        <table>
          <tr>
            <td>Status</td>
            <td><span id="state">OFF</span></td>
          </tr>
          <tr>
            <td>Capture Delay</td>
            <td><span id="captureDelay">1000</span> ms</td>
          </tr>
          <tr>
            <td>Capture Amount</td>
            <td><span id="captureAmount">1</span></td>
          </tr>
          <tr>
            <td>Save Captures</td>
            <td><span id="saveCaptures">TRUE</span></td>
          </tr>
        </table>
        <br />
        <div>
          <button id="changeSettings">Change Settings</button>
        </div>
      </div>
    </div>
    <dialog id="favDialog">
      <form method="dialog">
        <p>
          <b>Change Settings</b>
          <br>
          <br>
          <b>State Machine</b>
          <br>
          <br>
          <label for="newState">State:</label>
          <select id="newState" name="newState">
            <option id="OFF" disabled>OFF</option>
            <option id="STANDBY">STANDBY</option>
            <option id="LOW_POWER" disabled>LOW_POWER</option>
            <option id="STAR_TRACK">STAR_TRACK</option>
            <option id="CAPTURE_ONLY">CAPTURE_ONLY</option>
          </select>
          <br>
          <br>
          <label for="newCapDelay">Capture Delay (ms):</label>
          <input id="newCapDelay" type="number" step="1">
          <br>
          <br>
          <label for="newCapAmount">Capture Amount:</label>
          <input id="newCapAmount" type="number" step="1">
          <br>
          <br>
          <label for="newCapSave">Save Captures:</label>
          <input id="newCapSave" type="checkbox">
        </p>
        <div>
          <button id="cancel" type="reset">Cancel</button>
          <button id="submit" type="submit">Set</button>
        </div>
      </form>
    </dialog>
    <script>
      let lastDisplayImage;
      let lastCaptureTime = -1;
      const settingsButton = document.getElementById("changeSettings");
      const cancelButton = document.getElementById("cancel");
      const submitButton = document.getElementById("submit");
      const dialog = document.getElementById("favDialog");
      dialog.returnValue = "cancel";

      async function getData() {
       const url = `http://${window.location.host}/data`;
        return await fetch(url)
          .then(response => response.json())
          .then(data => {
            return data;
          });
      }

      async function setData(data) {
        const options = {
          "method": "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          "body": JSON.stringify(data),
        }

        const url = `http://${window.location.host}/data`;
        await fetch(url, options);
      }

      async function getImage() {
       const url = `http://${window.location.host}/image`;
        return await fetch(url)
          .then(response => response.json())
          .then(data => {
            return data.image;
          });
      }

      async function openCheck(dialog) {
        if (dialog.open) {
          const data = await getData();
          document.getElementById("newState").selectedIndex = data.status;
          document.getElementById("newCapSave").checked = data.capture.save_captures;
          document.getElementById("newCapDelay").value = data.capture.delay;
          document.getElementById("newCapAmount").value = data.capture.num_of_images;
        } else if (dialog.returnValue === "submit") {
          const newData = {
            "status": document.getElementById("newState").selectedOptions[0].id,
            "capture": {
              "delay": parseInt(document.getElementById("newCapDelay").value),
              "num_of_images": parseInt(document.getElementById("newCapAmount").value),
              "save_captures": document.getElementById("newCapSave").checked,
            },
          };
          setData(newData);
        }
      }

      /** Update button opens a modal dialog */
      settingsButton.addEventListener("click", () => {
        dialog.showModal();
        openCheck(dialog);
      });

      /** Form cancel button closes the dialog box */
      cancelButton.addEventListener("click", () => {
        dialog.close("cancel");
        openCheck(dialog);
      });

      /** Form submit button closes the dialog box */
      submitButton.addEventListener("click", () => {
        dialog.close("submit");
        openCheck(dialog);
      });

      /** Let the user download the display image */
      function downloadDisplayImage() {
        const unixTime = Math.floor(Date.now() / 1000);
        downloadFile(`star-tracker_capture_${unixTime}.jpg`, lastDisplayImage);
      }

      /** Let the user download a file */
      function downloadFile(filename, data) {
        console.log(filename);
        const byteCharacters = atob(data);
        const byteArrays = [];
        const sliceSize = 512;

        for (let offset = 0; offset < byteCharacters.length; offset += sliceSize) {
          const slice = byteCharacters.slice(offset, offset + sliceSize);

          const byteNumbers = new Array(slice.length);
          for (let i = 0; i < slice.length; i++) {
            byteNumbers[i] = slice.charCodeAt(i);
          }

          const byteArray = new Uint8Array(byteNumbers);
          byteArrays.push(byteArray);
        }

        const blob = new Blob(byteArrays, {
          type: "application/octet-stream",
        });

        const a = document.createElement("a");
        a.download = filename;
        a.href = window.URL.createObjectURL(blob);
        a.click();
      }

      /** Update all info / data being displayed */
      async function update() {
        const data = await getData();
        document.getElementById("state").innerHTML = data.status;
        document.getElementById("captureDelay").innerHTML = data.capture.delay;
        document.getElementById("captureAmount").innerHTML = data.capture.num_of_images;
        if (data.capture.save_captures === true) {
          document.getElementById("saveCaptures").innerHTML = "TRUE";
        } else {
          document.getElementById("saveCaptures").innerHTML = "FALSE";
        }

        // get last image capture for display
        if (data.status != "OFF" && data.camera.last_capture_time != lastCaptureTime) {
          lastCaptureTime = data.camera.last_capture_time;
          updateImage();
        }
      }

      async function updateImage() {
        lastDisplayImage = await getImage();
        document.getElementById("image").src = "data:image/jpeg;base64, " + lastDisplayImage;
      }

      updateImage();
      update();
      const interval = setInterval(function() {
        update();
      }, 1000);
    </script>
  </body>
</html>
