<template>
  <div id="container">
    <Sidebar :treeData="treeData" :currentPath="currentPath" :savedFiles="allAnnotations" @slide-selected="openSlide" />

    <div id="right-panel">
      <div id="viewer-top-panel">
        <label>Dosya Adı: <textarea v-model="fields.fileName" rows="1" /></label>
        <label>Organ: <textarea v-model="fields.organ" rows="1" /></label>
        <label>Teşhis: <textarea v-model="fields.diagnosis" rows="1" /></label>
        <label>Derecelendirme: <textarea v-model="fields.grading" rows="1" /></label>

        <div class="navigation-buttons-group">
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
      </div>

      <div id="viewer"></div>
    </div>

    <Notification v-if="notification" :message="notification.message" :success="notification.success" />
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch, provide } from 'vue';
import OpenSeadragon from 'openseadragon';
import Sidebar from './Sidebar.vue';
import Notification from './Notification.vue';

const treeData = ref({});
const currentPath = ref(null);
const viewer = ref(null);
const fabricOverlay = ref(null);
const allAnnotations = ref({});
const notification = ref(null);
const fileList = ref([]);
const currentIndex = ref(-1);

provide('allAnnotations', allAnnotations);

const fields = ref({
  fileName: '',
  organ: '',
  diagnosis: '',
  grading: ''
});

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

watch(treeData, (newTreeData) => {
  if (newTreeData && Object.keys(newTreeData).length > 0) {
    fileList.value = buildFileListFromTree(newTreeData);
  }
}, { deep: true, immediate: true });

watch(currentPath, (newPath) => {
  currentIndex.value = fileList.value.findIndex(f => f.path === newPath);
});

function showNotification(message, success = true) {
  notification.value = { message, success };
  setTimeout(() => (notification.value = null), 1500);
}

function openSlide(path) {
  if (currentPath.value === path) return;

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
    tileSources: `/slides/${path}.dzi`
  });

  viewer.value.addHandler('open', () => {
  fabricOverlay.value = viewer.value.fabricjsOverlay();
  const canvas = fabricOverlay.value.fabricCanvas();
  canvas.isDrawingMode = true;
  canvas.freeDrawingBrush.color = 'red';
  canvas.freeDrawingBrush.width = 5;
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

  const path = currentPath.value;
  const data = {
    timestamp: new Date().toISOString(),
    slidePath: path,
    ...fields.value,
    viewerState: {
      zoom: viewer.value.viewport.getZoom(),
      center: viewer.value.viewport.getCenter()
    }
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

    if (fileList.value.length > 0 && !currentPath.value) {
      openSlide(fileList.value[0].path);
    }

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

#viewer canvas {
  z-index: 1000 !important;
  pointer-events: auto !important;
}
</style>
