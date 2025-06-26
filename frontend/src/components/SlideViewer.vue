<template>
  <div id="container">
    <Sidebar :treeData="treeData" :currentPath="currentPath" :savedFiles="allAnnotations" @slide-selected="openSlide" />

    <div id="right-panel">
      <div id="viewer-top-panel">
        <label>Dosya Adı: <textarea v-model="fields.fileName" rows="1" /></label>
        <label>Organ: <textarea v-model="fields.organ" rows="1" /></label>
        <label>Teşhis: <textarea v-model="fields.diagnosis" rows="1" /></label>
        <label>Derecelendirme: <textarea v-model="fields.grading" rows="1" /></label>
        
        <!-- Navigation -->
        <div class="navigation-box">
          <h4>Navigation</h4>
          <div class="prev-next-column">
            <button @click="saveAnnotation">
              <img src="../assets/save.svg" alt="Kaydet" width="22" height="22" />
              <span>Kaydet</span>
            </button>
            <button @click="openPreviousSlide">
              <img src="../assets/previous.svg" alt="Geri" width="22" height="22" />
              <span>Geri</span>
            </button>
            <button @click="openNextSlide">
              <span>İleri</span>
              <img src="../assets/next.svg" alt="İleri" width="22" height="22" />
            </button>
          </div>
        </div>

        <!-- Tools -->
        <div class="tool-box">
          <h4>Tool</h4>
          <div class="tool-buttons-row">
            <div class="tool-buttons">
              <!-- Pan -->
              <button
                @click="clearTools"
                :disabled="!isViewerReady"
                :class="{ 'active-button': activeTool === null }"
              >
                <img src="../assets/pan.svg" alt="Pan" width="22" height="22" />
              </button>
              <!-- Brush -->
              <button
                @click="setBrushTool"
                :disabled="!isViewerReady"
                :class="{ 'active-button': activeTool === 'brush' }"
              >
                <img src="../assets/brush.svg" alt="Brush" width="22" height="22" />
              </button>
              <!-- BBox -->
              <button
                @click="setRectTool"
                :disabled="!isViewerReady"
                :class="{ 'active-button': activeTool === 'bbox' }"
              >
                <img src="../assets/bbox.svg" alt="BBox" width="22" height="22" />
              </button>
              <!-- Undo (aktiflik kontrolü gerekmez) -->
              <button
                @click="undo"
                :disabled="historyIndex <= 0"
              >
                <img src="../assets/undo.svg" alt="Undo" width="22" height="22" />
              </button>

              <!-- Delete -->
              <button
                @click="deleteSelected"
                :disabled="!selectedDeletableObject"
                :class="{ active: activeTool === 'delete' }">
                <img src="../assets/delete.svg" alt="Delete" width="22" height="22" />
              </button>
            </div>
            <div class="brush-settings" v-if="isViewerReady && showBrushSettings">
              <label v-if="activeTool === 'brush'">Renk: <input type="color" v-model="brushSettings.color" /></label>
              <label>Kalınlık: <input type="range" min="1" max="50" v-model="brushSettings.brushsize" /></label>
            </div>
          </div>
        </div>

        <!-- Label Info -->
        <div class="label-info-box" v-if="labels.length > 0">
          <h4>Etiketler</h4>
          <div v-for="(item, i) in labels" :key="i" class="label-item">
            <div
              class="color-sample"
              :style="{ backgroundColor: item.color }"
              v-if="item.type === 'brush'"
            ></div>
            <div v-else class="bbox-sample">▭</div>
            <span>{{ item.label }}</span>
          </div>
        </div>
      </div>

      <div id="viewer"></div>
    </div>

    <Notification v-if="notification" :message="notification.message" :success="notification.success" />
  </div>
</template>


<script setup>
import { ref, onMounted, nextTick, watch, provide } from 'vue';
import OpenSeadragon from 'openseadragon';
import { fabric, initFabricJSOverlay } from '@adamjarling/openseadragon-fabricjs-overlay';
import Sidebar from './Sidebar.vue';
import Notification from './Notification.vue';
import { computed } from 'vue';


const selectedDeletableObject = ref(null);

const canDelete = computed(() => {
  const canvas = fabricOverlay.value?.fabricCanvas();
  const activeObj = canvas?.getActiveObject();
  return (
    !activeTool.value && // Pan modunda olmalı
    !!activeObj &&
    activeObj.customType !== 'labelText' // Etiket text'i değilse
  );
});


initFabricJSOverlay(OpenSeadragon, fabric);

const treeData = ref({});
const currentPath = ref(null);
const viewer = ref(null);
const fabricOverlay = ref(null);
const allAnnotations = ref({});
const notification = ref(null);
const fileList = ref([]);
const currentIndex = ref(-1);
const isViewerReady = ref(false);
const activeTool = ref(null);
const showBrushSettings = ref(false);
const history = ref([]);
let historyIndex = -1;
const labels = ref([]);

provide('allAnnotations', allAnnotations);

const brushSettings = ref({
  color: '#2e85d6',
  brushsize: 30,
  opacity: 1
});

const fields = ref({
  fileName: '',
  organ: '',
  diagnosis: '',
  grading: ''
});

function removeAssociatedLabel(canvas, targetObj) {
  const labelObjs = canvas.getObjects().filter(obj => obj.customType === 'labelText');
  const threshold = 10; // konumsal tolerans (zoom'a göre ayarlanabilir)

  labelObjs.forEach(label => {
    const dx = Math.abs((label.left || 0) - (targetObj.left || 0));
    const dy = Math.abs((label.top || 0) - ((targetObj.top || 0) - 20)); // çünkü label yukarıda
    if (dx < threshold && dy < threshold) {
      canvas.remove(label);
    }
  });
}


function addLabelText(canvas, obj, label) {
  const zoom = canvas.getZoom() || 1;
  const color = obj.stroke || obj.fill || 'rgba(0,0,0,0.5)';

  const text = new fabric.Text(label, {
    left: obj.left,
    top: obj.top - 20,
    fill: 'white',
    fontSize: 24 / zoom,
    backgroundColor: color,  // ✅ çizimle aynı renk
    selectable: false,
    evented: false,
    customType: 'labelText',
    hasControls: false,
    hasBorders: false
  });

  canvas.add(text);
}



function updateLabelsFromCanvas(canvas) {
  const newLabels = [];
  canvas.getObjects().forEach(obj => {
    if (obj.label && obj.customType !== 'labelText') {
      const color = obj.stroke || obj.fill || '#ccc';
      const type = obj.type === 'path' ? 'brush' : 'bbox';
      newLabels.push({ label: obj.label, color, type });
    }
  });
  labels.value = newLabels;
}

function promptLabel(callback) {
  const label = prompt("Etiket girin:");
  if (label && label.trim() !== "") {
    callback(label.trim());
  }
}

function saveHistory() {
  const canvas = fabricOverlay.value.fabricCanvas();
  if (historyIndex < history.value.length - 1) {
    history.value.splice(historyIndex + 1);
  }
  const json = canvas.toJSON(['label', 'customType']);
  history.value.push(json);
  historyIndex = history.value.length - 1;
}

function undo() {
  const canvas = fabricOverlay.value.fabricCanvas();
  if (historyIndex > 0) {
    historyIndex--;
    canvas.loadFromJSON(history.value[historyIndex], () => {
      canvas.renderAll();
      canvas.getObjects().forEach(obj => {
        if (obj.label && obj.customType !== 'labelText') {
          addLabelText(canvas, obj, obj.label);
        }
      });
      updateLabelsFromCanvas(canvas);
    });
  }
}

function deleteSelected() {
  const canvas = fabricOverlay.value.fabricCanvas();
  const obj = selectedDeletableObject.value;

  if (obj) {
    // Bağlı label text'ini de kaldır
    const labelText = canvas.getObjects().find(o =>
      o.customType === 'labelText' && Math.abs(o.left - obj.left) < 5 && Math.abs(o.top - (obj.top - 20)) < 5
    );

    canvas.remove(obj);
    if (labelText) canvas.remove(labelText);

    selectedDeletableObject.value = null;
    canvas.discardActiveObject();
    canvas.renderAll();
    saveHistory();
    updateLabelsFromCanvas(canvas);
  }
}



function hexToRgbA(hex, opacity) {
  let c;
  if (/^#([A-Fa-f0-9]{3}){1,2}$/.test(hex)) {
    c = hex.substring(1).split('');
    if (c.length === 3) c = [c[0], c[0], c[1], c[1], c[2], c[2]];
    c = '0x' + c.join('');
    const r = (c >> 16) & 255;
    const g = (c >> 8) & 255;
    const b = c & 255;
    return `rgba(${r},${g},${b},${opacity})`;
  }
  throw new Error('Bad Hex');
}

function clearTools() {
  activeTool.value = null;
  showBrushSettings.value = false;
  const canvas = fabricOverlay.value?.fabricCanvas();
  if (canvas) {
    canvas.isDrawingMode = false;
    canvas.selection = false;
    canvas.off('mouse:down');
    canvas.off('mouse:move');
    canvas.off('mouse:up');
    canvas.off('path:created');
  }
  viewer.value.setMouseNavEnabled(true);
}

function updateBrushSettings() {
  if (!fabricOverlay.value) return;
  const canvas = fabricOverlay.value.fabricCanvas();
  canvas.freeDrawingBrush = new fabric.PencilBrush(canvas);
  canvas.freeDrawingBrush.color = hexToRgbA(brushSettings.value.color, brushSettings.value.opacity);
  canvas.freeDrawingBrush.width = brushSettings.value.brushsize;
}

function deactivateTools() {
  if (!fabricOverlay.value) return;
  const canvas = fabricOverlay.value.fabricCanvas();
  canvas.isDrawingMode = false;
  canvas.selection = false;
  canvas.off('mouse:down');
  canvas.off('mouse:move');
  canvas.off('mouse:up');
  canvas.off('path:created');
  canvas.getObjects().forEach(obj => {
    if (obj.customType !== 'labelText') {
      obj.selectable = false;
      obj.evented = false;
    }
    obj.hasControls = false;
    obj.hasBorders = false;
    if (obj.setCoords) obj.setCoords();
  });
  fabricOverlay.value.fabricCanvas().discardActiveObject();
  fabricOverlay.value.fabricCanvas().renderAll();
  viewer.value.setMouseNavEnabled(true);
}

function setBrushTool() {
  if (!fabricOverlay.value) return showNotification("Görüntü henüz yüklenmedi", false);

  deactivateTools();
  activeTool.value = 'brush';
  showBrushSettings.value = true;

  const canvas = fabricOverlay.value.fabricCanvas();
  const brush = new fabric.PencilBrush(canvas);
  brush.width = brushSettings.value.brushsize;
  brush.color = hexToRgbA(brushSettings.value.color, brushSettings.value.opacity);
  canvas.freeDrawingBrush = brush;

  canvas.isDrawingMode = true;
  canvas.selection = false;

  canvas.off('path:created');
  canvas.on('path:created', (e) => {
    const path = e.path;
    promptLabel((label) => {
      path.label = label;
      addLabelText(canvas, path, label);
      saveHistory();
      updateLabelsFromCanvas(canvas);
    });
  });

  viewer.value.setMouseNavEnabled(false);
}


const buildFileListFromTree = (data, path = []) => {
  return Object.entries(data).flatMap(([key, val]) => {
    if (key === 'files') {
      return val.map(file => ({ path: [...path, file].join('/') }));
    } else if (typeof val === 'object') {
      return buildFileListFromTree(val, [...path, key]);
    }
    return [];
  });
};

function setRectTool() {
  if (!fabricOverlay.value) return showNotification("Görüntü henüz yüklenmedi", false);
  deactivateTools();
  showBrushSettings.value = false;
  activeTool.value = 'bbox';
  const canvas = fabricOverlay.value.fabricCanvas();
  let rect, isDown, origX, origY;
  canvas.on('mouse:down', function (o) {
    if (activeTool.value !== 'bbox') return;
    isDown = true;
    const pointer = canvas.getPointer(o.e);
    origX = pointer.x;
    origY = pointer.y;
    rect = new fabric.Rect({
      left: origX,
      top: origY,
      width: 0,
      height: 0,
      fill: 'rgba(255,0,0,0.2)',
      stroke: 'red',
      strokeWidth: 2,
      selectable: false,
      evented: false,
      hasControls: false,
      hasBorders: false
    });
    canvas.add(rect);
  });
  canvas.on('mouse:move', function (o) {
    if (!isDown || activeTool.value !== 'bbox') return;
    const pointer = canvas.getPointer(o.e);
    rect.set({
      width: Math.abs(pointer.x - origX),
      height: Math.abs(pointer.y - origY),
      left: pointer.x > origX ? origX : pointer.x,
      top: pointer.y > origY ? origY : pointer.y
    });
    canvas.renderAll();
  });
  canvas.on('mouse:up', function () {
    if (activeTool.value !== 'bbox') return;
    isDown = false;
    if (rect) {
      promptLabel((label) => {
        rect.label = label;
        addLabelText(canvas, rect, label);
        saveHistory();
        updateLabelsFromCanvas(canvas);
      });
    }
  });
  viewer.value.setMouseNavEnabled(false);
}

function showNotification(message, success = true) {
  notification.value = { message, success };
  setTimeout(() => (notification.value = null), 1500);
}

watch(treeData, (newTreeData) => {
  if (newTreeData && Object.keys(newTreeData).length > 0) {
    fileList.value = buildFileListFromTree(newTreeData);
  }
}, { deep: true, immediate: true });

watch(currentPath, (newPath) => {
  currentIndex.value = fileList.value.findIndex(f => f.path === newPath);
});

watch(() => brushSettings.value.color, updateBrushSettings);
watch(() => brushSettings.value.opacity, updateBrushSettings);
watch(() => brushSettings.value.brushsize, updateBrushSettings);



function openSlide(path) {
  if (currentPath.value === path) return;
  isViewerReady.value = false;
  const parts = path.split('/');
  fields.value = {
    fileName: parts.at(-1),
    organ: parts[0],
    diagnosis: parts[1],
    grading: ''
  };
  viewer.value?.destroy();
  viewer.value = OpenSeadragon({
    id: 'viewer',
    prefixUrl: 'https://cdnjs.cloudflare.com/ajax/libs/openseadragon/4.0.0/images/',
    tileSources: `/slides/${path}.dzi`,
    showNavigator: true
  });
  viewer.value.addHandler('open', () => {
    fabricOverlay.value = viewer.value.fabricjsOverlay({ fabricCanvasOptions: { selection: false } });
    fabricOverlay.value.resizeCanvas();
    const canvas = fabricOverlay.value.fabricCanvas();
    history.value = [];
    historyIndex = -1;
    const saved = allAnnotations.value?.[path]?.annotations;
    if (saved) {
      canvas.loadFromJSON(saved, () => {
        canvas.renderAll();
        canvas.getObjects().forEach(obj => {
          if (obj.label && obj.customType !== 'labelText') {
            addLabelText(canvas, obj, obj.label);
          }
        });
        updateLabelsFromCanvas(canvas);
        saveHistory();
      });
      canvas.on('selection:created', (e) => {
      const obj = e.target;
      if (obj && obj.label && obj.customType !== 'labelText') {
        selectedDeletableObject.value = obj;
      }
    });

    canvas.on('selection:cleared', () => {
      selectedDeletableObject.value = null;
    });

    } else {
      saveHistory();
    }
    isViewerReady.value = true;
  });
  currentPath.value = path;
  nextTick(() => {
    const activeFile = document.querySelector(`.file[title="${path}"]`);
    if (activeFile) {
      document.querySelectorAll('.file.active').forEach(el => el.classList.remove('active'));
      activeFile.classList.add('active');
      activeFile.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  });
}

function openNextSlide() {
  if (fileList.value.length === 0) return showNotification("Dosya yok", false);
  if (currentIndex.value < fileList.value.length - 1) openSlide(fileList.value[currentIndex.value + 1].path);
  else showNotification("Son dosya", false);
}

function openPreviousSlide() {
  if (fileList.value.length === 0) return showNotification("Dosya yok", false);
  if (currentIndex.value > 0) openSlide(fileList.value[currentIndex.value - 1].path);
  else showNotification("İlk dosya", false);
}

function saveAnnotation() {
  if (!viewer.value) return;
  const canvas = fabricOverlay.value.fabricCanvas();
  const canvasJson = canvas.toJSON(['label', 'customType']);
  const path = currentPath.value;
  const data = {
    timestamp: new Date().toISOString(),
    slidePath: path,
    ...fields.value,
    viewerState: {
      zoom: viewer.value.viewport.getZoom(),
      center: viewer.value.viewport.getCenter()
    },
    annotations: canvasJson
  };
  allAnnotations.value[path] = data;
  fetch('/api/save-annotations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(allAnnotations.value)
  })
    .then(res => res.ok ? showNotification("Kayıt başarılı!") : showNotification("Kayıt hatası!", false))
    .catch(err => showNotification("Hata: " + err.message, false));
  markFileAsSaved(path);
}

function markFileAsSaved(path) {
  const fileEl = document.querySelector(`.file[title="${path}"]`);
  fileEl?.classList.add('saved');
}

onMounted(async () => {
  try {
    const [annotationsRes, treeRes] = await Promise.all([
      fetch('/api/get-annotations').then(res => res.json()),
      fetch('/api/tree').then(res => res.json())
    ]);
    allAnnotations.value = annotationsRes || {};
    treeData.value = treeRes || {};
    fileList.value = buildFileListFromTree(treeData.value);
    if (fileList.value.length > 0 && !currentPath.value) openSlide(fileList.value[0].path);
    nextTick(() => {
      Object.keys(allAnnotations.value).forEach(path => markFileAsSaved(path));
    });
  } catch (err) {
    console.error("Yükleme hatası:", err);
    showNotification("Veri yüklenemedi", false);
  }
});
</script>

<style scoped>
@import '../assets/styles.css';

/* Navigation Buttons */

.navigation-box {
  border: 1px solid #444;
  border-radius: 8px;
  padding: 10px;
  background-color: #1f1f1f;
  width: auto;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 10px;
}

.navigation-box h4 {
  margin: 0 0 5px 0;
  color: white;
  font-weight: bold;
  border-bottom: 1px solid #555;
  padding-bottom: 4px;
}

.navigation-box button {
  padding: 8px 12px;
  background-color: #333;
  color: white;
  border: 1px solid #666;
  border-radius: 5px;
  padding: 6px 10px;
  cursor: pointer;
  font-size: 18px;
  font-weight: 300;
  min-width: 50px;
  height: 40px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.2);
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.navigation-box button:hover {
  background-color: #3e8dcf;
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0,0,0,0.25);
}

.navigation-box button:active {
  transform: scale(0.98);
}

/* Navigation Buttons */

/* Prev Next Column */
.prev-next-column {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
}

/* Prev Next Column */

#viewer canvas {
  z-index: 1000 !important;
  pointer-events: auto !important;
}

.tool-box {
  border: 1px solid #444;
  border-radius: 8px;
  padding: 10px;
  background-color: #1f1f1f;
  width: auto;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tool-box h4 {
  margin: 0 0 5px 0;
  color: white;
  font-weight: bold;
  border-bottom: 1px solid #555;
  padding-bottom: 4px;
}

.tool-buttons-row {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 12px;
}

.tool-buttons {
  display: flex;
  gap: 8px;
}

.tool-buttons button {
  background-color: #333;
  color: white;
  border: 1px solid #666;
  border-radius: 5px;
  padding: 6px 10px;
  cursor: pointer;
}

.tool-buttons button:hover {
  background-color: #3e8dcf;
}
.tool-buttons button.active-button {
  background-color: #3e8dcf !important;
  border-color: #3e8dcf;
  color: white;
  box-shadow: 0 0 0 2px rgba(62, 141, 207, 0.3);
}

.tool-buttons button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  pointer-events: none;
}



.brush-settings label {
  display: flex;
  align-items: center;
  gap: 6px;
  color: white;
  font-size: 14px;
}

.brush-settings input[type="range"] {
  width: 100px;
}


/* Viewer */
#viewer {
  position: relative;
  height: 600px;
  flex-grow: 1;
  background-color: #0e0e0e;
  margin-top: 10px;
}

#viewer-top-panel {
  padding: 8px 12px;
  min-height: unset;
  display: flex;
  justify-content: flex-start; 
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 8px;
}

#viewer-top-panel label {
  margin: 0 0 5px 0;
  color: #aaa;
  font-size: 14px;
  text-align: left;
}

#viewer-top-panel textarea {
  width: 100%;
  min-height: 50px;
  resize: none;
  padding: 8px;
  background-color: #2e2e2e;
  color: #eee;
  border: 1px solid #444;
  border-radius: 4px;
  box-sizing: border-box;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.5;
  word-wrap: break-word;
}

/* Viewer */

/* Info Box */

.label-info-box {
  border: 1px solid #444;
  border-radius: 8px;
  padding: 10px;
  background-color: #1f1f1f;
  color: white;
  margin-top: 10px;
  width: 200px;
}

.label-item {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}

.color-sample {
  width: 20px;
  height: 20px;
  border-radius: 3px;
  border: 1px solid #ccc;
}

.bbox-sample {
  width: 20px;
  height: 20px;
  border: 2px solid white;
  text-align: center;
  line-height: 20px;
  font-size: 14px;
}


</style>
