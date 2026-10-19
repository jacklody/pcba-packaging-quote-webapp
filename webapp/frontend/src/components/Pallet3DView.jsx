import { useEffect, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

function disposeObject(root) {
  root.traverse((obj) => {
    if (obj.geometry) obj.geometry.dispose();
    if (obj.material) {
      for (const m of Array.isArray(obj.material) ? obj.material : [obj.material]) m.dispose();
    }
  });
}

export default function Pallet3DView({ palletView }) {
  const containerRef = useRef(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || !palletView) return;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf7f9fb);

    const width = container.clientWidth;
    const height = container.clientHeight;
    const camera = new THREE.PerspectiveCamera(45, width / height, 1, 20000);

    const pl = palletView.pallet.l;
    const pw = palletView.pallet.w;
    const ph = palletView.pallet.h;
    const box = palletView.box;
    const { layers, placed_boxes: placedBoxes = [] } = palletView.layout;

    camera.position.set(pl * 1.4, palletView.total_height_mm * 1.3, pw * 1.8);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(window.devicePixelRatio);
    container.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.target.set(0, (ph + layers * box.h) / 2, 0);

    scene.add(new THREE.AmbientLight(0xffffff, 0.65));
    const dirLight = new THREE.DirectionalLight(0xffffff, 1.1);
    dirLight.position.set(pl, pw * 2, pl);
    scene.add(dirLight);

    const palletGeo = new THREE.BoxGeometry(pl, ph, pw);
    const palletMat = new THREE.MeshStandardMaterial({ color: 0xb08954 });
    const pallet = new THREE.Mesh(palletGeo, palletMat);
    pallet.position.y = ph / 2;
    scene.add(pallet);

    const palletEdges = new THREE.LineSegments(
      new THREE.EdgesGeometry(palletGeo),
      new THREE.LineBasicMaterial({ color: 0x7a5c33 })
    );
    palletEdges.position.copy(pallet.position);
    scene.add(palletEdges);

    // 纯渲染：坐标、层数、旋转角全部来自后端 placed_boxes，前端不再计算排布
    const boxGeo = new THREE.BoxGeometry(box.l, box.h, box.w);
    const boxMat = new THREE.MeshStandardMaterial({ color: 0x7fa8d9, transparent: true, opacity: 0.9 });
    const boxEdgesGeo = new THREE.EdgesGeometry(boxGeo);
    const boxEdgeMat = new THREE.LineBasicMaterial({ color: 0x33547a });

    placedBoxes.forEach((placed) => {
      const mesh = new THREE.Mesh(boxGeo, boxMat.clone());
      mesh.position.set(placed.x_mm, placed.y_mm, placed.z_mm);
      mesh.rotation.y = (placed.rotation_y_deg || 0) * Math.PI / 180;
      scene.add(mesh);
      const edges = new THREE.LineSegments(boxEdgesGeo, boxEdgeMat);
      edges.position.copy(mesh.position);
      edges.rotation.copy(mesh.rotation);
      scene.add(edges);
    });

    let raf;
    const animate = () => {
      raf = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    const resizeObserver = new ResizeObserver(() => {
      const w = container.clientWidth;
      const h = container.clientHeight;
      if (w === 0 || h === 0) return;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    });
    resizeObserver.observe(container);

    return () => {
      cancelAnimationFrame(raf);
      resizeObserver.disconnect();
      controls.dispose();
      disposeObject(scene);
      renderer.dispose();
      container.removeChild(renderer.domElement);
    };
  }, [palletView]);

  return <div ref={containerRef} className="view3d" />;
}
