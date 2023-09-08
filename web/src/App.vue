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


/**
 * 
x轴代表时间，y轴代表波峰值，y取值范围-1至1，x轴是一个圆圈的范围，取值在-1至1之间，这个点的坐标让它运动起来非常美妙，有节奏和韵律感，注重有趣的动态变化和运动规律

 */
 function generateSound(frequencies, duration, sampleRate) {
  const samples = [];
  const numSamples = Math.floor(duration * sampleRate);
  const amplitude = 1; // Maximum amplitude for normalized audio
  const centerX = 0; // X coordinate of center
  const centerY = 0; // Y coordinate of center
  const radius = 1; // Radius of the circle

  for (let i = 0; i < numSamples; i++) {
    const t = i / sampleRate;
    const angle = t * 2 * Math.PI;
    const x = centerX + radius * Math.cos(angle);
    const y = centerY + radius * Math.sin(angle);
    let sample = 0;

    for (let j = 0; j < frequencies.length; j++) {
      sample += amplitude * y * Math.sin(2 * Math.PI * frequencies[j] * t);
    }

    samples.push([x,sample]);
  }

  return samples;
}

const frequencies = [440, 880, 1320]; // Frequencies of A4, A5, and E6
const duration = 10; // 1 second
const sampleRate = 44100; // 44.1 kHz


window._index=0;
const _sounds=generateSound(frequencies, duration, sampleRate);;
const getPosition=()=>{
  const pos=new Vector2(..._sounds[window._index])
        window._index++;
        if(_sounds.length<=window._index) window._index=0;
      console.log(pos)
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

      this.$refs.renderer.onBeforeRender(() => {
        const pos= getPosition()
        this.raycaster.setFromCamera(pos, this.$refs.renderer.three.camera);
        this.raycaster.ray.intersectPlane(this.pointerPlane, this.pointerV3);
        const x = 2 * this.pointerV3.x / this.WIDTH;
        const y = 2 * this.pointerV3.y / this.HEIGHT;
        this.liquidEffect.addDrop(x, y, 0.025, 0.005);
      });
      

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