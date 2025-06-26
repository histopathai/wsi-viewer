<template>
  <div id="notification" :style="{ backgroundColor: success ? '#4CAF50' : '#f44336' }">
    {{ message }}
  </div>
</template>

<script setup>
defineProps({
  message: String,
  success: Boolean
});
</script>

<style scoped>
#notification {
  display: block;
  position: fixed;
  top: 20px;
  right: 20px;
  padding: 10px 20px;
  color: white;
  border-radius: 5px;
  z-index: 1000;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
}
</style>
