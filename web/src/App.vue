<template>
  <Renderer ref="renderer" antialias :pointer="{ onMove: onPointerMove }" :orbit-ctrl="{ enableDamping: true }"
    resize="window">
    <Camera :position="{ z: 10 }" />


    <Scene ref="scene">

      <AmbientLight />
      <PointLight :color="light1Color" :position="{ x: 50, y: 50, z: 50 }" />
      <PointLight :color="light2Color" :position="{ x: -50, y: 50, z: 50 }" />
      <PointLight :color="light3Color" :position="{ x: -50, y: -50, z: 50 }" />
      <PointLight :color="light4Color" :position="{ x: 50, y: -50, z: 50 }" />

      <LiquidPlane ref="liquid" :width="WIDTH" :height="HEIGHT" :width-segments="512" :height-segments="512"
        :color="color" :metalness="metalness" :roughness="roughness" />
    </Scene>

  </Renderer>
</template>



<script>

import { Plane, Raycaster, Vector3,Vector2 } from 'three';
import {Pane} from 'tweakpane';
import chroma from 'chroma-js';
import {
  AmbientLight,
  Camera,
  PointLight,
  Renderer,
  Scene,
} from 'troisjs';
import LiquidPlane from 'troisjs/src/components/liquid/LiquidPlane.js';
import WaveSurfer from 'wavesurfer.js'


function createSound(){
  const duration = 5; // 持续时间（秒）
const sampleRate = 44100; // 采样率（每秒采样次数）
const frequency = 440; // 基准频率（Hz）

const numSamples = duration * sampleRate; // 总采样数
const samples = new Float32Array(numSamples); // 存储采样值的数组

for (let i = 0; i < numSamples; i++) {
  const t = i / sampleRate; // 当前时间（秒）
  const value = Math.sin(2 * Math.PI * frequency * t); // 正弦函数取值
  samples[i] = value;
}
console.log(samples); // 输出采样值数组
return samples
}

window._index=0;
const _sounds=createSound();
const getPosition=()=>{
  const pos=new Vector2(_sounds[window._index],0)
        window._index++;
    return pos
}

export default {
  components: {
    AmbientLight,
    Camera,
    LiquidPlane,
    PointLight,
    Renderer,
    Scene,
  },
  setup() {
    return {
      WIDTH: 30,
      HEIGHT: 30,
    };
  },
  data() {
    return {
      color: '#ffffff',
      metalness: 1,
      roughness: 0.2,
      light1Color: '#FFFF80',
      light2Color: '#DE3578',
      light3Color: '#FF4040',
      light4Color: '#0d25bb',
    };
  },
  mounted() {
    
    this.pointer = this.$refs.renderer.three.pointer;
    this.liquidEffect = this.$refs.liquid.liquidEffect;
    this.liquidEffect.addDrop(0, 0, 0.05, 0.05);

    // custom raycaster
    this.raycaster = new Raycaster();
    this.pointerPlane = new Plane(new Vector3(0, 0, 1), 0);
    this.pointerV3 = new Vector3();

    this.pane = new Pane();
    this.pane.addBinding(this, 'color');
    this.pane.addBinding(this, 'metalness', { min: 0, max: 1 });
    this.pane.addBinding(this, 'roughness', { min: 0, max: 1 });
    this.pane.addButton({ title: 'Random lights' }).on('click', this.randomColors);

    this.pane.addButton({ title: 'Random sound' }).on('click', this.randomSound);

  },
  unmounted() {
    this.pane.dispose();
  },
  methods: {
    onPointerMove() {
      this.raycaster.setFromCamera(this.pointer.positionN, this.$refs.renderer.three.camera);
      this.raycaster.ray.intersectPlane(this.pointerPlane, this.pointerV3);
      const x = 2 * this.pointerV3.x / this.WIDTH;
      const y = 2 * this.pointerV3.y / this.HEIGHT;
      this.liquidEffect.addDrop(x, y, 0.025, 0.005);

      // -1,1   | 1,1
      // -1,-1  | 1,-1
      console.log(this.pointer.positionN)
      

    },
    randomColors() {
      this.light1Color = chroma.random().hex();
      this.light2Color = chroma.random().hex();
      this.light3Color = chroma.random().hex();
      this.light4Color = chroma.random().hex();
    },
    randomSound(){

//       const wavesurfer = WaveSurfer.create({
//   container: '#waveform',
//   waveColor: '#4F4A85',
//   progressColor: '#383351',
//   url: '/audio.mp3',
// })

      // fetch()
      
        requestAnimationFrame(()=>{
          const pos= getPosition()
        this.raycaster.setFromCamera(pos, this.$refs.renderer.three.camera);
        this.raycaster.ray.intersectPlane(this.pointerPlane, this.pointerV3);
        const x = 2 * this.pointerV3.x / this.WIDTH;
        const y = 2 * this.pointerV3.y / this.HEIGHT;
        this.liquidEffect.addDrop(x, y, 0.025, 0.005);
        })

    }
  },
};



</script>

<style>
body {
  margin: 0;
}

canvas {
  display: block;
}
</style>