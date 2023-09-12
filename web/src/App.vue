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
import WaveSurfer from 'wavesurfer.js'
import { Plane, Raycaster, Vector3,Vector2,InstancedBufferAttribute, Object3D } from 'three';
import {Pane} from 'tweakpane';
import chroma from 'chroma-js';
import {
  AmbientLight,
  Camera,
  PointLight,
  Renderer,
  Scene,BoxGeometry,BasicMaterial,Mesh,InstancedMesh,
  PhongMaterial,
} from 'troisjs';
import LiquidPlane from 'troisjs/src/components/liquid/LiquidPlane.js';
import Pitchfinder from 'pitchfinder'
 

const _prompts=[
"The golden sunlight filters through the colorful autumn leaves.",
"The crisp autumn air is filled with the warmth of the sun.",
"The gentle breeze carries the scent of fallen leaves in the autumn sunshine.",
"The sunlight dances on the surface of the tranquil lake, creating a mesmerizing scene.",
"As the sun sets, the autumn sky is painted with hues of orange and pink.",
"Walking under the warm autumn sun, I feel a sense of peace and tranquility.",
"The sun-kissed meadows in autumn are a sight to behold.",
"The sun's rays illuminate the changing foliage, creating a breathtaking autumn landscape.",
"The golden sunlight casts long shadows as I stroll through the park in autumn.",
"The autumn sun sets the trees ablaze with vibrant shades of red, orange, and yellow.",
"The gentle touch of the autumn sun warms my skin and lifts my spirits.",
"The autumn sunlight filters through the branches, casting a mesmerizing pattern on the ground.",
"The golden sunlight bathes the city in a warm glow, making the autumn streets come alive.",
"In the soft autumn sunlight, I find solace and serenity.",
"The golden hour of autumn bathes everything in a magical light.",
"The warm autumn sunlight creates a cozy atmosphere, perfect for sipping a cup of tea.",
"The autumn sun peeks through the clouds, creating a dramatic and enchanting scene.",
"The golden rays of the autumn sun illuminate the path ahead, guiding me on my journey.",
"The autumn sunsets are a breathtaking spectacle, painting the sky in shades of orange and purple.",
"Under the autumn sun, the world seems to slow down, allowing me to appreciate the beauty around me."
]

// 随机取元素的方法
function getRandomPrompt() {
  // 生成一个随机的索引
  var randomIndex = Math.floor(Math.random() * _prompts.length);
  // 返回对应索引的元素
  return _prompts[randomIndex];
}


const pitchWorker = (data) => {
  const { peaks, sampleRate = 32000, algo = 'AMDF' } =  data
  const detectPitch = Pitchfinder[algo]({ sampleRate })
  const duration = peaks.length / sampleRate
  const bpm = peaks.length / duration / 60

  const frequencies = Pitchfinder.frequencies(detectPitch, peaks, {
    tempo: bpm,
    quantization: bpm,
  })

  // Find the baseline frequency (the value that appears most often)
  const frequencyMap = {}
  let maxAmount = 0
  let baseFrequency = 0
  frequencies.forEach((frequency) => {
    if (!frequency) return
    const tolerance = 10
    frequency = Math.round(frequency * tolerance) / tolerance
    if (!frequencyMap[frequency]) frequencyMap[frequency] = 0
    frequencyMap[frequency] += 1
    if (frequencyMap[frequency] > maxAmount) {
      maxAmount = frequencyMap[frequency]
      baseFrequency = frequency
    }
  })

  return {
    frequencies,
    baseFrequency,
  }
}




// // fetch()
      // fetch('http://127.0.0.1:3013/run_inference/', {
      //   method: 'POST',
      //   headers: {
      //     'Content-Type': 'application/json'
      //   },
      //   body: JSON.stringify({ text  })
      // })
      //   .then(response => response.json())
      //   .then(data => {
      //     const {audio}=data;
      //     if(audio){
      //       sounds.push(audio);
      //       randomGet()
      //     }
      //   })
      //   .catch(error => console.log(error));



const sounds=[]


export default {
  components: {
    AmbientLight,
    Camera,
    LiquidPlane,
    PointLight,
    Renderer,
    Scene
  },
 
  setup() {
    const SIZE = 1.6, NX = 25, NY = 25, PADDING = 1;
    const SIZEP = SIZE + PADDING;
    const W = NX * SIZEP - PADDING;
    const H = NY * SIZEP - PADDING;
    return {
      SIZE, NX, NY, PADDING,
      SIZEP, W, H,
      NUM_INSTANCES: NX * NY,
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
    this.renderer = this.$refs.renderer;
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

    this.pane.addButton({ title: 'Create' }).on('click', this.create);

    this.pane.addButton({ title: 'Random sound' }).on('click', this.randomSound);

 
    this.renderer.onBeforeRender(this.animate);
  },
  unmounted() {
    this.pane.dispose();
  },
  methods: {
    animate() {
      this.updateInstanceMatrix();
    },
    updateInstanceMatrix() {
    
    },
    onPointerMove() {
      // this.raycaster.setFromCamera(this.pointer.positionN, this.$refs.renderer.three.camera);
      // this.raycaster.ray.intersectPlane(this.pointerPlane, this.pointerV3);
      // const x = 2 * this.pointerV3.x / this.WIDTH;
      // const y = 2 * this.pointerV3.y / this.HEIGHT;
      // this.liquidEffect.addDrop(x, y, 0.025, 0.005);

      // -1,1   | 1,1
      // -1,-1  | 1,-1
      // console.log(this.pointer.positionN)
    },
    randomColors() {
      this.light1Color = chroma.random().hex();
      this.light2Color = chroma.random().hex();
      this.light3Color = chroma.random().hex();
      this.light4Color = chroma.random().hex();
    },
    create(){
      const text=getRandomPrompt()
      create(text)
 
    },
    randomSound(){
  
//       const wavesurfer = WaveSurfer.create({
//   container: '#waveform',
//   waveColor: '#4F4A85',
//   progressColor: '#383351',
//   url: '/audio.mp3',
// })



const randomGet=(soundObj)=>{
  
  const _x=Math.random()*0.9
  const _y=Math.random()*0.9

const w=document.createElement('div');
const p=createCard("text",soundObj.images[[Math.floor(Math.random() * soundObj.images.length)]])

document.body.appendChild(w);
document.body.appendChild(p);

p.className='poster';
 
  p.querySelector('.drop-down-window').addEventListener('click',()=>{
    wavesurfer.play()
  })

  p.style.top =  `calc(${_y*100}% - 140px)`
  p.style.left= `calc(${_x*100}% - 90px)`

  // document.querySelector('#waveform').innerHTML='';
  const audio = soundObj.audios[Math.floor(Math.random() * soundObj.audios.length)];

let peaks,duration,length;
const height = 500,items=[];

const wavesurfer = WaveSurfer.create({
  container: w,
  waveColor: '#4F4A85',
  progressColor: 'white',
  autoplay:false,
  url: audio,
  renderFunction: (channels, ctx) => {
    const { width, height } = ctx.canvas
    const scale = channels[0].length / width
    const step = 10

    ctx.translate(0, height / 2)
    ctx.strokeStyle = ctx.fillStyle
    ctx.beginPath()

    for (let i = 0; i < width; i += step * 2) {
      const index = Math.floor(i * scale)
      const value = Math.abs(channels[0][index])
      let x = i
      let y = value * height

      ctx.moveTo(x, 0)
      ctx.lineTo(x, y)
      ctx.arc(x + step / 2, y, step / 2, Math.PI, 0, true)
      ctx.lineTo(x + step, 0)

      x = x + step
      y = -y
      ctx.moveTo(x, 0)
      ctx.lineTo(x, y)
      ctx.arc(x + step / 2, y, step / 2, Math.PI, 0, false)
      ctx.lineTo(x + step, 0)
    }

    ctx.stroke()
    ctx.closePath()
  },
})


wavesurfer.on('ready',e=>{
  const data=wavesurfer.getDecodedData()
  peaks =data.getChannelData(0);
  duration=data.duration
 
  const {frequencies,baseFrequency, }=pitchWorker({peaks, sampleRate:wavesurfer.options.sampleRate})
  length=frequencies.length;
  let prevY = 0

  frequencies.forEach((frequency, index) => {
    if (!frequency) return
    const y =Math.round (height - (frequency / (baseFrequency * 2)) * height)
    items.push(y*(y > prevY?1:-1)/height)
    prevY = y
  })

  console.log('ready',peaks )

  
})

wavesurfer.on('timeupdate',e=>{
  let index=Math.round(items.length*e/duration)
 
  let pos=new Vector2(...convertPointToB(_x,_y))
  // console.log('timeupdate',pos)

     this.raycaster.setFromCamera(pos, this.$refs.renderer.three.camera);
this.raycaster.ray.intersectPlane(this.pointerPlane, this.pointerV3);
const x = 2 * this.pointerV3.x / this.WIDTH;
const y = 2 * this.pointerV3.y / this.HEIGHT;
this.liquidEffect.addDrop(x, y, 0.125,0.01* items[index]||0);


})


wavesurfer.on('finish',e=>{
  this.light1Color = chroma.random().hex();
      this.light2Color = chroma.random().hex();
      this.light3Color = chroma.random().hex();
      this.light4Color = chroma.random().hex();
  //     const sound=sounds[Math.floor(Math.random() * sounds.length)];
  // randomGet(sound) 
})

}

document.querySelector('#waveform').innerHTML='';

  const sound=sounds[Math.floor(Math.random() * sounds.length)];
  randomGet(sound)

    }
  },
};

function createCard(text,url){
  let div=document.createElement('div');
  div.innerHTML=`<div class='card'>
  <div class='img-cont'>
    <span class='drop-down-window'>PLAY</span>
    <img class='img' src="${url}" alt="">
  </div>
  <div class='content-cont'>
    <span class='card-header'>Standard</span>
    <span class='card-body'>${text}</span>
  </div>
</div>`
return div
}


function create(text){
  fetch('http://127.0.0.1:3013/run_inference/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ text,duration:8 })
})
  .then(response => response.json())
  .then(data => {
    const {audio,images}=data;
    let sound={
      audios:['data:audio/wav;base64,'+audio.base64],
      images:Array.from(images,im=>{
        return 'data:image/png;base64,'+im.base64
      })
    }
    sounds.push(sound)
  })
  .catch(error => console.log(error));
}


function convertPointToB(x_A, y_A) {
  var x_B = (2 * x_A) - 1;
  var y_B = (2 * y_A) - 1;
  return [x_B,  -y_B ]
}

</script>

<style>
body {
  margin: 0;
}

canvas {
  display: block;
}
</style>