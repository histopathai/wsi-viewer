<template>
  <div class="folder" :class="{ open: isOpen, closed: !isOpen }">
    <div class="folder-label" @click="toggleFolder">
      <span class="folder-icon">
        <img src="../assets/folder.svg" alt="icon" width="22" height="22" />
      </span>
      {{ label }}
    </div>
    <div class="children" v-if="isOpen">
      <template v-for="(val, key) in data" :key="key">
        <Folder
          v-if="typeof val === 'object' && key !== 'files'"
          :label="key"
          :data="val"
          :path="[...path, key]"
          :currentPath="currentPath"
          :savedFiles="savedFiles"
          @slide-clicked="emitClick"
        />
        <div
          v-if="key === 'files'"
          v-for="file in val"
          :key="file"
          class="file"
          :class="{ active: isActive(file), saved: isFileSaved(file) }"
          :title="getFullPath(file)"
          @click="emitClick(getFullPath(file))"
        >
          <span class="file-icon">
            <img src="../assets/pathology.svg" alt="icon" width="22" height="22" />
          </span>
          {{ file }}
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue';
import Folder from './Folder.vue';

const props = defineProps({
  data: Object,
  label: String,
  path: Array,
  currentPath: String,
  savedFiles: Object
});

const emit = defineEmits(['slide-clicked']);
const isOpen = ref(false);

const shouldBeOpen = computed(() => props.currentPath?.startsWith(props.path.join('/')));

watch(() => props.currentPath, () => {
  if (shouldBeOpen.value && !isOpen.value) isOpen.value = true;
});

const isFileSaved = (file) => props.savedFiles?.[getFullPath(file)];
const isActive = (file) => getFullPath(file) === props.currentPath;
const toggleFolder = (e) => { e.stopPropagation(); isOpen.value = !isOpen.value; };
const emitClick = (path) => emit('slide-clicked', path);
const getFullPath = (file) => [...props.path, file].join('/');
</script>

<style scoped>
@import '../assets/styles.css';
</style>
