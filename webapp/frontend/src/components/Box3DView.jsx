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

function addEdges(scene, mesh, color = 0x33547a) {
  const edges = new THREE.LineSegments(new THREE.EdgesGeometry(mesh.geometry), new THREE.LineBasicMaterial({ color }));
  edges.position.copy(mesh.position);
  scene.add(edges);
}

export default function Box3DView({ boxView }) {
  const containerRef = useRef(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || !boxView) return;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf7f9fb);

    const width = container.clientWidth;
    const height = container.clientHeight;
    const camera = new THREE.PerspectiveCamera(45, width / height, 1, 10000);
    const ob = boxView.outer_box;
    const diag = Math.hypot(ob.l, ob.w, ob.h);
    camera.position.set(diag * 1.2, diag * 0.9, diag * 1.5);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(window.devicePixelRatio);
    container.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.target.set(0, ob.h / 2, 0);

    scene.add(new THREE.AmbientLight(0xffffff, 0.6));
    const dirLight = new THREE.DirectionalLight(0xffffff, 1.2);
    dirLight.position.set(diag, diag * 1.5, diag);
    scene.add(dirLight);

    const boxGeo = new THREE.BoxGeometry(ob.l, ob.h, ob.w);
    const boxMat = new THREE.MeshStandardMaterial({ color: 0x1a73e8, transparent: true, opacity: 0.18, depthWrite: false });
    const outerBox = new THREE.Mesh(boxGeo, boxMat);
    outerBox.position.y = ob.h / 2;
    scene.add(outerBox);
    addEdges(scene, outerBox);

    const p = boxView.product;
    const layout = boxView.inner_layout || {};
    const productMat = new THREE.MeshStandardMaterial({ color: 0xf5a623 });
    const dividerMat = new THREE.MeshStandardMaterial({ color: 0xd8b36a, transparent: true, opacity: 0.72 });
    const foamMat = new THREE.MeshStandardMaterial({ color: 0x9fd2a8, transparent: true, opacity: 0.55 });

    if (layout.type === "divider_grid" && Array.isArray(layout.placed_items) && layout.placed_items.length) {
      // 纯渲染：每件产品、每张刀卡的坐标尺寸都来自后端求解器
      // 后端坐标约定 x=箱长 y=箱宽 z=箱高，原点在箱内底面角；three.js 用中心坐标
      const cardGeoFor = (card) => {
        if (card.axis === "x") return { size: [card.thickness_mm, card.span_b_mm, card.span_a_mm], pos: [card.position_mm - ob.l / 2, card.span_b_mm / 2 - ob.h / 2, card.span_a_mm / 2 - ob.w / 2] };
        if (card.axis === "y") return { size: [card.span_a_mm, card.span_b_mm, card.thickness_mm], pos: [card.span_a_mm / 2 - ob.l / 2, card.span_b_mm / 2 - ob.h / 2, card.position_mm - ob.w / 2] };
        return { size: [card.span_a_mm, card.thickness_mm, card.span_b_mm], pos: [card.span_a_mm / 2 - ob.l / 2, card.position_mm - ob.h / 2, card.span_b_mm / 2 - ob.w / 2] };
      };
      (layout.divider_cards || []).forEach((card) => {
        const { size, pos } = cardGeoFor(card);
        const mesh = new THREE.Mesh(new THREE.BoxGeometry(size[0], size[1], size[2]), dividerMat);
        mesh.position.set(pos[0], pos[1], pos[2]);
        scene.add(mesh);
      });

      layout.placed_items.forEach((item) => {
        const mesh = new THREE.Mesh(
          new THREE.BoxGeometry(item.dx_mm, item.dz_mm, item.dy_mm),
          productMat
        );
        mesh.position.set(item.x_mm - ob.l / 2, item.z_mm - ob.h / 2, item.y_mm - ob.w / 2);
        scene.add(mesh);
        addEdges(scene, mesh, 0x9a5f00);
      });
    } else if (layout.type === "foam_cavity") {
      const buffer = layout.buffer_thickness_mm || 30;
      const foamLeft = new THREE.Mesh(new THREE.BoxGeometry(buffer, p.h + buffer, p.w + buffer), foamMat);
      foamLeft.position.set(-p.l / 2 - buffer / 2, ob.h / 2, 0);
      scene.add(foamLeft);
      const foamRight = new THREE.Mesh(new THREE.BoxGeometry(buffer, p.h + buffer, p.w + buffer), foamMat);
      foamRight.position.set(p.l / 2 + buffer / 2, ob.h / 2, 0);
      scene.add(foamRight);
      const product = new THREE.Mesh(new THREE.BoxGeometry(p.l, p.h, p.w), productMat);
      product.position.y = ob.h / 2;
      scene.add(product);
      addEdges(scene, product, 0x9a5f00);
    } else {
      const product = new THREE.Mesh(new THREE.BoxGeometry(p.l, p.h, p.w), productMat);
      product.position.y = ob.h / 2;
      scene.add(product);
      addEdges(scene, product, 0x9a5f00);
    }

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
  }, [boxView]);

  return <div ref={containerRef} className="view3d" />;
}
