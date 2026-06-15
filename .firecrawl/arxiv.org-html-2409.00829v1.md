[![logo](https://services.dev.arxiv.org/html/static/arxiv-logomark-small-white.svg)Back to arXiv](https://arxiv.org/)

[Back to abstract page](https://arxiv.org/abs/2409.00829v1)

[![logo](https://services.dev.arxiv.org/html/static/arxiv-logo-one-color-white.svg)Back to arXiv](https://arxiv.org/)

This is **experimental HTML** to improve accessibility. We invite you to report rendering errors. Use Alt+Y to toggle on accessible reporting links and Alt+Shift+Y to toggle off. Learn more [about this project](https://info.arxiv.org/about/accessible_HTML.html) and [help improve conversions](https://info.arxiv.org/help/submit_latex_best_practices.html).


[Why HTML?](https://info.arxiv.org/about/accessible_HTML.html) [Report Issue](https://arxiv.org/html/2409.00829v1/#myForm) [Back to Abstract](https://arxiv.org/abs/2409.00829v1) [Download PDF](https://arxiv.org/pdf/2409.00829v1)

## Table of Contents

1. [Abstract](https://arxiv.org/html/2409.00829v1#abstract "Abstract")
2. [1 Introduction](https://arxiv.org/html/2409.00829v1#S1 "In Curvy: A Parametric Cross-section based Surface Reconstruction")
3. [2 Related work](https://arxiv.org/html/2409.00829v1#S2 "In Curvy: A Parametric Cross-section based Surface Reconstruction")   1. [2.1 Pointcloud generation](https://arxiv.org/html/2409.00829v1#S2.SS1 "In 2 Related work ‣ Curvy: A Parametric Cross-section based Surface Reconstruction")
2. [2.2 Surface reconstruction](https://arxiv.org/html/2409.00829v1#S2.SS2 "In 2 Related work ‣ Curvy: A Parametric Cross-section based Surface Reconstruction")
4. [3 Approach](https://arxiv.org/html/2409.00829v1#S3 "In Curvy: A Parametric Cross-section based Surface Reconstruction")   1. [3.1 Adaptive Splitting](https://arxiv.org/html/2409.00829v1#S3.SS1 "In 3 Approach ‣ Curvy: A Parametric Cross-section based Surface Reconstruction")
2. [3.2 Training on parametric space](https://arxiv.org/html/2409.00829v1#S3.SS2 "In 3 Approach ‣ Curvy: A Parametric Cross-section based Surface Reconstruction")      1. [3.2.1 Permutation Invariance and Neighborhoods](https://arxiv.org/html/2409.00829v1#S3.SS2.SSS1 "In 3.2 Training on parametric space ‣ 3 Approach ‣ Curvy: A Parametric Cross-section based Surface Reconstruction")
      2. [3.2.2 Learning Point Cloud Representation](https://arxiv.org/html/2409.00829v1#S3.SS2.SSS2 "In 3.2 Training on parametric space ‣ 3 Approach ‣ Curvy: A Parametric Cross-section based Surface Reconstruction")
      3. [3.2.3 Cross-Section Attention](https://arxiv.org/html/2409.00829v1#S3.SS2.SSS3 "In 3.2 Training on parametric space ‣ 3 Approach ‣ Curvy: A Parametric Cross-section based Surface Reconstruction")
      4. [3.2.4 Adapting for Variable Cross-sections](https://arxiv.org/html/2409.00829v1#S3.SS2.SSS4 "In 3.2 Training on parametric space ‣ 3 Approach ‣ Curvy: A Parametric Cross-section based Surface Reconstruction")
      5. [3.2.5 Training Details](https://arxiv.org/html/2409.00829v1#S3.SS2.SSS5 "In 3.2 Training on parametric space ‣ 3 Approach ‣ Curvy: A Parametric Cross-section based Surface Reconstruction")
      6. [3.2.6 Training details](https://arxiv.org/html/2409.00829v1#S3.SS2.SSS6 "In 3.2 Training on parametric space ‣ 3 Approach ‣ Curvy: A Parametric Cross-section based Surface Reconstruction")
5. [4 Results and Discussion](https://arxiv.org/html/2409.00829v1#S4 "In Curvy: A Parametric Cross-section based Surface Reconstruction")   1. [4.1 Cross-section dependence](https://arxiv.org/html/2409.00829v1#S4.SS1 "In 4 Results and Discussion ‣ Curvy: A Parametric Cross-section based Surface Reconstruction")
2. [4.2 Failure Cases](https://arxiv.org/html/2409.00829v1#S4.SS2 "In 4 Results and Discussion ‣ Curvy: A Parametric Cross-section based Surface Reconstruction")
6. [5 Comparisons](https://arxiv.org/html/2409.00829v1#S5 "In Curvy: A Parametric Cross-section based Surface Reconstruction")
7. [6 Conclusion and Future Scope](https://arxiv.org/html/2409.00829v1#S6 "In Curvy: A Parametric Cross-section based Surface Reconstruction")
8. [References](https://arxiv.org/html/2409.00829v1#bib "References")

HTML conversions [sometimes display errors](https://info.dev.arxiv.org/about/accessibility_html_error_messages.html) due to content that did not convert correctly from the source. This paper uses the following packages that are not yet supported by the HTML conversion tool. Feedback on these issues are not necessary; they are known and are being worked on.

- failed: tikzscale
- failed: epic

Authors: achieve the best HTML results from your LaTeX submissions by following these [best practices](https://info.arxiv.org/help/submit_latex_best_practices.html).

[License: CC BY 4.0](https://info.arxiv.org/help/license/index.html#licenses-available)

arXiv:2409.00829v1 \[cs.CV\] 01 Sep 2024

# Curvy: A Parametric Cross-section based Surface Reconstruction

Report issue for preceding element

Aradhya N. Mathur

IIITD

aradhyam@iiitd.ac.inApoorv Khattar

The University of Manchester

apoorv.khattar@postgrad.manchester.ac.ukDr. Ojaswa Sharma

IIITD

ojaswa@iiitd.ac.in

Report issue for preceding element

###### Abstract

Report issue for preceding element

In this work, we present a novel approach for reconstructing shape point clouds using planar sparse cross-sections with the help of generative modeling. We present unique challenges pertaining to the representation and reconstruction in this problem setting. Most methods in the classical literature lack the ability to generalize based on object class and employ complex mathematical machinery to reconstruct reliable surfaces. We present a simple learnable approach to generate a large number of points from a small number of input cross-sections over a large dataset. We use a compact parametric polyline representation using adaptive splitting to represent the cross-sections and perform learning using a Graph Neural Network to reconstruct the underlying shape in an adaptive manner reducing the dependence on the number of cross-sections provided.

Report issue for preceding element

## 1 Introduction

Report issue for preceding element

Surface reconstruction from cross-sections is a well-explored problem. There is a rich literature on methods demonstrating the generation of reliable surfaces from cross-sections. Little work exists that provides insights into how complex objects could be generated using cross-sections with the help of deep learning methods that could provide an added advantage of capturing semantic context associated with shapes. Deep learning-based methods can provide better generalizability qualities associated with unseen shapes of similar types. Unlike traditional methods of surface generation from incomplete point clouds, the problem of surface reconstruction from cross-sections brings unique challenges that we aim to address in this paper. Previous approaches for point cloud completion have focused on generating point clouds from images or representation learning using autoencoders. Several previous methods focused on generating surfaces using cross-sections and did not involve any learning based on the class of objects. Our method can be used with any modern encoder-decoder-based point cloud generation since it focuses on learning the latent embeddings rather than generating the point cloud directly.
Our approach introduces a novel input representation for the cross-sections, aiming to capture crucial information that would be overlooked when using surface-sampled points. Point clouds, while dense in most areas, often suffer from incomplete information in certain regions. In contrast, cross-section curves exhibit a highly non-uniform distribution of information, necessitating reconstruction methods capable of handling sparse and anisotropic data. By considering this unique characteristic of cross-sections, our approach enables a more comprehensive and accurate reconstruction of shapes. Our contributions can be summarised as follows:

Report issue for preceding element

1. 1.


An approach for learning surface reconstruction based on parametric representation of cross-sections,

Report issue for preceding element

2. 2.


A novel framework for generating a point cloud while adapting to the anisotropic and sparse nature of input cross-sections. This constitutes two attention mechanisms to focus on the local and global structure of the cross-sections and show their significance empirically through an ablation study, and

Report issue for preceding element

3. 3.


A new dataset for parametric representation of cross-sections.

Report issue for preceding element


## 2 Related work

Report issue for preceding element

Surface reconstruction is a widely studied problem in computer graphics. As methods for representing 3D data change, so do the methods for shape reconstruction. The different methods for representing 3D data include a voxel-based representation that gives information pertaining to points in a discrete grid, point clouds that contain the locations of information, and meshes that have added neighborhood information in the form of an adjacency matrix corresponding to the points. Newer implicit methods directly target surface generation by learning to produce the implicit field functions.
We divide this section based on the representation of the output for different methods.

Report issue for preceding element

### 2.1 Pointcloud generation

Report issue for preceding element

There are two primary approaches that have been explored for point cloud reconstruction. Reconstruction of point clouds has been done using multi-view/single-view images and partial-point clouds.

Report issue for preceding element

A deep autoencoder network for the reconstruction of point clouds results in compact representations and can perform semantic operations, interpolations, and shape completion  \[ [1](https://arxiv.org/html/2409.00829v1#bib.bib1 "")\],\[ [17](https://arxiv.org/html/2409.00829v1#bib.bib17 "")\]. These networks leverage 1-D and 2-D convolutional layers to extract latent representation for the generation of point clouds.
Single image point cloud generation has also been performed hierarchically from low resolution by gradually upsampling the point cloud as explored in \[ [6](https://arxiv.org/html/2409.00829v1#bib.bib6 "")\]. This multi-stage process uses EMD distance \[ [6](https://arxiv.org/html/2409.00829v1#bib.bib6 "")\] and computes Chamfer distance for the later stages w.r.t. ground truth dense point cloud. Another approach uses a multi-resolution tree-structured network that allows to process point clouds for 3D shape understanding and generation \[ [8](https://arxiv.org/html/2409.00829v1#bib.bib8 "")\].
Some newer methods also approach this problem from a local supervision perspective to understand the local geometry better \[ [11](https://arxiv.org/html/2409.00829v1#bib.bib11 "")\].
Further, skip-attention has shown to play an important role in tasks such as point cloud completion \[ [25](https://arxiv.org/html/2409.00829v1#bib.bib25 "")\]. The architecture proposed consists of primarily three parts - a point cloud encoder,
a decoder that generates the point cloud, and skip-attention layers that fuse relevant features from the encoder to the decoder at different resolutions.
Reinforcement learning has also been explored with GANs trained for point cloud generation. The agent is trained to predict a good seed value for the adversarial reconstruction of incomplete point clouds \[ [20](https://arxiv.org/html/2409.00829v1#bib.bib20 "")\]. The method uses an autoencoder trained on complete point clouds to generate the global feature vector (GFV) and a GAN that is trained to produce GFV. The pipeline uses GFV generated from an incomplete point cloud as a state and supplies it to an RL agent which the GAN uses to generate GFV close to the GFV of a complete point cloud.

Report issue for preceding element

### 2.2 Surface reconstruction

Report issue for preceding element

One of the seminal works \[ [19](https://arxiv.org/html/2409.00829v1#bib.bib19 "")\] proposes constructing 2D geometric shapes from 1D cross-sections. The method provides sampling conditions to guarantee the correct topology and closeness to the original shape for the Hausdorff distance.
One of the early works \[ [12](https://arxiv.org/html/2409.00829v1#bib.bib12 "")\] proposes a manifold mesh reconstruction method from unorganized points with arbitrary topology. The method proposed defines a two-step process for reliably reconstructing the geometric shape from an unorganized point cloud sampled from its surface.

Report issue for preceding element

Early works took inspiration from medical imaging problems. A two-step process for the reconstruction of a surface from cross-sections has been proposed by first computing the arrangement for the cross-section within each cell and then reconstructing an approximation of the object. This is done by performing its intersection with the cell boundary and gluing the pieces back together to yield the surface \[ [3](https://arxiv.org/html/2409.00829v1#bib.bib3 "")\]. An algorithm for non-parallel cross-sections consisting of curve networks of arbitrary shape and topology has also been developed \[ [18](https://arxiv.org/html/2409.00829v1#bib.bib18 "")\].
Several methods propose implicit field-based reconstruction. One such method utilizes sign agnostic learning for geometric shapes \[ [2](https://arxiv.org/html/2409.00829v1#bib.bib2 "")\]. This method uses a deep learning-based approach that allows learning of implicit shape representations directly from unsigned raw data like point clouds and triangle soups. The proposed unsigned distance loss family possesses plane reproduction property based on suitable initialization of the network weights.

Report issue for preceding element

The surface reconstruction method has also been performed with topological constraints \[ [16](https://arxiv.org/html/2409.00829v1#bib.bib16 "")\]. This method relies on computing candidates for cell partitioning of ambient volume. The method is based on the calculation of a single surface patch per cell so that the connected manifold surface of some topology is obtained. 3D surface reconstruction from unorganized planar cross-sections using a split-merge approach using Hermite mean-value interpolation for triangular meshes has also been used \[ [22](https://arxiv.org/html/2409.00829v1#bib.bib22 "")\].
A divide-and-conquer optimization-based strategy can also be employed to perform topology-constrained reconstruction \[ [28](https://arxiv.org/html/2409.00829v1#bib.bib28 "")\]. New methods like Orex \[ [21](https://arxiv.org/html/2409.00829v1#bib.bib21 "")\] leverage deep learning for cross-section to surface generation.

Report issue for preceding element

## 3 Approach

Report issue for preceding element![Refer to caption](https://arxiv.org/html/2409.00829v1/extracted/5826454/images/banner_test/gcn_blender_shadows_graph_only2.jpg)Figure 1: Overview of our reconstruction approach. Starting from a parametric representation of the given cross-sections, we train a network to generate a surface point cloud.Report issue for preceding element

In this work, we develop an approach for shape reconstruction from a set of unorganized cross-sections. We design a deep neural network that learns the overall structure of various shapes and generates a point cloud representing the original object.

Report issue for preceding element

Our approach can be defined as a three-step process. We first generate a large number of cross-sections from 3D models and sample them to create input cross-sectional data. Then surface points are sampled to generate a point cloud on which an autoencoder is trained to reconstruct the point cloud. In the final step, we use the encoded vector obtained from the autoencoder and train a Graph Neural Network on the parametric representation of input cross-sections to generate an embedding vector in a GAN-based setting to match the encoded vector for the same object. These embedding vectors can then be decoded to obtain the point cloud from the _pre-trained_ autoencoder network.

Report issue for preceding element

The cross-sections may be obtained as points sampled along a shape’s boundary that can further be represented as a polyline. However, for complex cross-sections, we would want a representation that optimally captures the curvature-related information. Instead of sampling points, we convert an entire cross-section curve into its parametric representation. This allows us to reduce any loss of information that may occur due to sampling and further helps reduce the memory requirements needed to represent a large number of points in the network. Let’s assume the density of points ρ𝜌\\rhoitalic\_ρ per unit length of a cross-section curve of length l𝑙litalic\_l. Depending on the sampling density ρ𝜌\\rhoitalic\_ρ, the number of points in a curve can vary, and for better information capture we need a high ρ𝜌\\rhoitalic\_ρ value to capture the curvature accurately. We note that the parametric curve can be represented using a fixed number of coefficients from which any arbitrary density of points can be sampled. Our overall approach is shown in Figure  [1](https://arxiv.org/html/2409.00829v1#S3.F1 "Figure 1 ‣ 3 Approach ‣ Curvy: A Parametric Cross-section based Surface Reconstruction").
The parametric curve fitting is further discussed in the supplementary.

Report issue for preceding element

### 3.1 Adaptive Splitting

Report issue for preceding element

It is important to ensure that a simpler piece (such as a straight line) is represented by fewer points so that more points can be assigned to a piece with many sharp turns.
We propose an adaptive splitting scheme for non-uniform distribution between pieces using the Douglas Peucker polyline simplification algorithm \[ [5](https://arxiv.org/html/2409.00829v1#bib.bib5 "")\] for finding a set of endpoints to generate the pieces within the curve. This helps to save more points for complex curves and uses fewer points for simpler curves further retaining more information than a uniform splitting scheme. Douglas Peucker algorithm is run for multiple iterations till the final number of unique endpoints returned is more than k𝑘kitalic\_k, we select the k𝑘kitalic\_k points with maximum absolute angle, where the angle varies between −9090-90\- 90 and +9090+90\+ 90. Once we have obtained k𝑘kitalic\_k pieces, we fit piece-wise polynomials as further discussed in the supplementary.

Report issue for preceding element

### 3.2 Training on parametric space

Report issue for preceding element

We take the ShapeNet dataset \[ [4](https://arxiv.org/html/2409.00829v1#bib.bib4 "")\] and use the manifold meshes. The input cross-sections are generated using mesh-plane intersection
and converted to parametric representation. Further in the text, cross-sections shall refer to the parametric representation of cross-sections. We sample surface points from the meshes; thus, each set of cross-sections and the corresponding point clouds form the input and the corresponding ground truth for the network. In order to use parameters with a neural network there are certain properties that the operations on the parametric representation must possess. Each piece of a cross-section is represented as a tensor in ℝ6×3superscriptℝ63\\mathbb{R}^{6\\times 3}blackboard\_R start\_POSTSUPERSCRIPT 6 × 3 end\_POSTSUPERSCRIPT of coefficients of the parametric representation fj⁢(t)subscript𝑓𝑗𝑡f\_{j}(t)italic\_f start\_POSTSUBSCRIPT italic\_j end\_POSTSUBSCRIPT ( italic\_t ) of degree 5 in ℝ3superscriptℝ3\\mathbb{R}^{3}blackboard\_R start\_POSTSUPERSCRIPT 3 end\_POSTSUPERSCRIPT. See Figure [2](https://arxiv.org/html/2409.00829v1#S3.F2 "Figure 2 ‣ 3.2 Training on parametric space ‣ 3 Approach ‣ Curvy: A Parametric Cross-section based Surface Reconstruction") for our parametric curve representation and its corresponding graph.

Report issue for preceding element

![Refer to caption](https://arxiv.org/html/2409.00829v1/extracted/5826454/images/piecewise.jpg)Figure 2: Converting a piecewise parametric representation of a cross-section (left) to a graph (right). The nodes in the graph are matrices of coefficients of the parametric functions.Report issue for preceding element

#### 3.2.1 Permutation Invariance and Neighborhoods

Report issue for preceding element

We represent the coefficients of the parametric representation as a vector for the neural network to act on. Thus, the cross-sections are represented as tensors containing the vector for each parametric piece. Further, the cross-sections contain neighborhood information in the form of adjacency of the pieces.

Report issue for preceding element

Therefore, the operations that we perform on the cross-sections must be permutation invariant since any combination of cross-sections represents the same object.
Given a set of m𝑚mitalic\_m parameterized cross-sections where each cross-section is partitioned into k𝑘kitalic\_k pieces with the coefficient matrix ΘlsubscriptΘ𝑙\\Theta\_{l}roman\_Θ start\_POSTSUBSCRIPT italic\_l end\_POSTSUBSCRIPT of the parametric functions for the lt⁢hsuperscript𝑙𝑡ℎl^{th}italic\_l start\_POSTSUPERSCRIPT italic\_t italic\_h end\_POSTSUPERSCRIPT piece, the full set of stacked coefficients for the entire set of cross-sections are represented as the tensor
𝒞=\[Θ1,Θ2,⋯,Θm\]⊺𝒞superscriptmatrixsubscriptΘ1subscriptΘ2⋯subscriptΘ𝑚⊺\\mathcal{C}=\\begin{bmatrix}\\Theta\_{1},\\Theta\_{2},\\cdots,\\Theta\_{m}\\end{bmatrix%
}^{\\intercal}caligraphic\_C = \[ start\_ARG start\_ROW start\_CELL roman\_Θ start\_POSTSUBSCRIPT 1 end\_POSTSUBSCRIPT , roman\_Θ start\_POSTSUBSCRIPT 2 end\_POSTSUBSCRIPT , ⋯ , roman\_Θ start\_POSTSUBSCRIPT italic\_m end\_POSTSUBSCRIPT end\_CELL end\_ROW end\_ARG \] start\_POSTSUPERSCRIPT ⊺ end\_POSTSUPERSCRIPT
of size m×(p+1)⁢k×3𝑚𝑝1𝑘3m\\times(p+1)k\\times 3italic\_m × ( italic\_p + 1 ) italic\_k × 3.
Any permutation of rows of 𝒞𝒞\\mathcal{C}caligraphic\_C still represents the same set of cross-sections (that is to say that the cross-sections can come in any order) and any circular permutation of these pieces represents the same cross-section. Therefore, any operation performed on 𝒞𝒞\\mathcal{C}caligraphic\_C should ideally yield the same result irrespective of the ordering of its rows and any circular permutation within each row.
Within a neural network, representations are created using matrix multiplications, and different orders of the rows and columns of 𝒞𝒞\\mathcal{C}caligraphic\_C would produce different results since,

Report issue for preceding element

|     |     |     |
| --- | --- | --- |
|  | W⊺⁢𝒞≠W⊺⁢S′⁢(𝒞),superscript𝑊⊺𝒞superscript𝑊⊺superscript𝑆′𝒞W^{\\intercal}\\mathcal{C}\\neq W^{\\intercal}S^{\\prime}(\\mathcal{C}),italic\_W start\_POSTSUPERSCRIPT ⊺ end\_POSTSUPERSCRIPT caligraphic\_C ≠ italic\_W start\_POSTSUPERSCRIPT ⊺ end\_POSTSUPERSCRIPT italic\_S start\_POSTSUPERSCRIPT ′ end\_POSTSUPERSCRIPT ( caligraphic\_C ) , |  |

where W𝑊Witalic\_W is a weight matrix and S′superscript𝑆′S^{\\prime}italic\_S start\_POSTSUPERSCRIPT ′ end\_POSTSUPERSCRIPT is a shuffle operation. Therefore we do away with this matrix-based representation. We create a graph-based representation using the piecewise parametric representation. We note that each cross-section has some adjacency information since the pieces of a cross-section are arranged in linear order along the contour. In order to use the neighborhood properties, we propose a graph-based representation, where each node is represented as the matrix of coefficients of a piece of the parametric curve and each edge denotes the adjacency. The graph-based representation allows our approach to take into account the desired permutation invariance while enabling us to use the additional adjacency information as needed.
Therefore, our final representation uses coefficients of the pieces where the adjacency matrix stores the piece-level relations.

Report issue for preceding element

![Refer to caption](https://arxiv.org/html/2409.00829v1/extracted/5826454/images/pipeline_arch.jpg)Figure 3: During training, the graph embedding decoder tries to generate an embedding that is similar to the point cloud embedding generated from the pre-trained encoder. This representation is then used by the decoder to generate the point cloud of a relevant shape.Report issue for preceding element

#### 3.2.2 Learning Point Cloud Representation

Report issue for preceding element

We train a point cloud auto-encoder on the ground truth point cloud generated by sampling 2048 points from the manifold meshes and then use the encoder embedding from this as the ground truth embedding similar to \[ [20](https://arxiv.org/html/2409.00829v1#bib.bib20 "")\], whereby a GAN is used to generate an embedding similar to that of a pre-trained point cloud auto-encoder which is very stable for training while allowing for stochasticity. Thus, the objective of the graph encoder is to learn the embedding from the cross-sections to produce a similar point cloud from the pre-trained decoder, as shown in Figure  [3](https://arxiv.org/html/2409.00829v1#S3.F3 "Figure 3 ‣ 3.2.1 Permutation Invariance and Neighborhoods ‣ 3.2 Training on parametric space ‣ 3 Approach ‣ Curvy: A Parametric Cross-section based Surface Reconstruction").

Report issue for preceding element

#### 3.2.3 Cross-Section Attention

Report issue for preceding element

Attention mechanism \[ [23](https://arxiv.org/html/2409.00829v1#bib.bib23 "")\] allows a network to focus on different features and enables better learning of the network. Taking inspiration from this, we introduce attention at two levels in our network for learning shapes.
We use two levels of cross-section attention mechanism, which we call _global attention_, and a piece-wise attention mechanism for focusing on local information. Each cross-section contains different amounts of information pertaining to the geometric shape of the object.
Similarly, within a cross-section, some pieces contain more information pertaining to the local regions, such as regions of high curvature. In order to focus on such regions, we introduce _local attention_, which attends to each piece within a cross-section.
The _global_ and _local_ attention are computed using Graph Attention \[ [24](https://arxiv.org/html/2409.00829v1#bib.bib24 "")\]. The normalized attention coefficient at the graph level can be expressed as αi,j=s⁢o⁢f⁢t⁢m⁢a⁢x⁢(ei,j)subscript𝛼𝑖𝑗𝑠𝑜𝑓𝑡𝑚𝑎𝑥subscript𝑒𝑖𝑗\\alpha\_{i,j}=softmax(e\_{i,j})italic\_α start\_POSTSUBSCRIPT italic\_i , italic\_j end\_POSTSUBSCRIPT = italic\_s italic\_o italic\_f italic\_t italic\_m italic\_a italic\_x ( italic\_e start\_POSTSUBSCRIPT italic\_i , italic\_j end\_POSTSUBSCRIPT ) where αi,jsubscript𝛼𝑖𝑗\\alpha\_{i,j}italic\_α start\_POSTSUBSCRIPT italic\_i , italic\_j end\_POSTSUBSCRIPT are the normalized attention coefficients for node i𝑖iitalic\_i in the graph, j∈𝒩i𝑗subscript𝒩𝑖j\\in\\mathcal{N}\_{i}italic\_j ∈ caligraphic\_N start\_POSTSUBSCRIPT italic\_i end\_POSTSUBSCRIPT where 𝒩isubscript𝒩𝑖\\mathcal{N}\_{i}caligraphic\_N start\_POSTSUBSCRIPT italic\_i end\_POSTSUBSCRIPT is the neighbourhood of node i𝑖iitalic\_i and ei,jsubscript𝑒𝑖𝑗e\_{i,j}italic\_e start\_POSTSUBSCRIPT italic\_i , italic\_j end\_POSTSUBSCRIPT is the attention coefficient. The attention coefficient is calculated using the same method as described in \[ [24](https://arxiv.org/html/2409.00829v1#bib.bib24 "")\].

Report issue for preceding element

First, attention is computed locally over the pieces of each cross-section, which we then aggregate into a single vector to represent each cross-section node. Finally, we apply the cross-section level attention for which we create a new adjacency matrix representing a complete graph. Since, at the cross-section level, there is no strict adjacency, representations for each cross-section must be learnable. We let the network perform attention on the complete graph giving it complete flexibility to attend to any cross-section. We still need to maintain the graph-level representation at this stage since we still require permutation invariance at this stage.

Report issue for preceding element

In our implementation, in order to restrict the attention to piece-level and cross-section levels, we explicitly pass the piece-level adjacency matrix during initial graph convolutions; this restricts the neighborhood of the nodes to attend within cross-sections, after which we aggregate the piece-level information and later replace the adjacency matrix with a complete graph adjacency.

Report issue for preceding element

|  | Aircraft | Chair | Sofa |
| --- | --- | --- | --- |
|  | Ground Truth | Predicted | Ground Truth | Predicted | Ground Truth | Predicted |
| --- | --- | --- | --- | --- | --- | --- |
| 10 cross-sections<br>Report issue for preceding element | ![Refer to caption](https://arxiv.org/html/2409.00829v1/) | ![Refer to caption](https://arxiv.org/html/2409.00829v1/) | ![Refer to caption](https://arxiv.org/html/2409.00829v1/) | ![Refer to caption](https://arxiv.org/html/2409.00829v1/) | ![Refer to caption](https://arxiv.org/html/2409.00829v1/) | ![Refer to caption](https://arxiv.org/html/2409.00829v1/) |
| 5 cross-sections<br>Report issue for preceding element | ![Refer to caption](https://arxiv.org/html/2409.00829v1/) | ![Refer to caption](https://arxiv.org/html/2409.00829v1/) | ![Refer to caption](https://arxiv.org/html/2409.00829v1/) | ![Refer to caption](https://arxiv.org/html/2409.00829v1/) | ![Refer to caption](https://arxiv.org/html/2409.00829v1/) | ![Refer to caption](https://arxiv.org/html/2409.00829v1/) |
| 2 cross-sections<br>Report issue for preceding element | ![Refer to caption](https://arxiv.org/html/2409.00829v1/) | ![Refer to caption](https://arxiv.org/html/2409.00829v1/) | ![Refer to caption](https://arxiv.org/html/2409.00829v1/) | ![Refer to caption](https://arxiv.org/html/2409.00829v1/) | ![Refer to caption](https://arxiv.org/html/2409.00829v1/) | ![Refer to caption](https://arxiv.org/html/2409.00829v1/) |

Figure 4:  (Left) Comparison of reconstruction quality with an increasing number of cross-sections. Input to the network is the set of cross-sections (red) belonging to the ground truth mesh(blue).
Report issue for preceding element

#### 3.2.4 Adapting for Variable Cross-sections

Report issue for preceding element

Since the network takes the input in the form of parametric cross-sections, where each cross-section consists of piecewise C1subscript𝐶1C\_{1}italic\_C start\_POSTSUBSCRIPT 1 end\_POSTSUBSCRIPT parametric curves, the parameters of the network become fixed during training if MLPs are used, prohibiting any changes in the number of cross-sections or pieces provided. In order to adapt to the variable nature of our data, we are further motivated to use the graph-based representation by allowing piece-level aggregation and cross-section level aggregation, which allows for a variable number of cross-sections to be provided to the network. Furthermore, we cannot use 1D-convolutions or 2-D convolutions directly in the parametric space because convolutions are not well defined on coefficient spaces.

Report issue for preceding element

We use graph convolutions in both the generator and discriminator. The discriminator is conditioned using the input graph parameters and predicts whether the generated embedding vector is real or fake, the input graph is converted to a graph-level embedding using successive graph convolutions \[ [15](https://arxiv.org/html/2409.00829v1#bib.bib15 "")\] and aggregation. Then the embedding vector is concatenated with the generated embedding and passed to subsequent layers. While the generator consisted of SAGEConv \[ [10](https://arxiv.org/html/2409.00829v1#bib.bib10 "")\] followed by DiffNorm \[ [27](https://arxiv.org/html/2409.00829v1#bib.bib27 "")\] to prevent over-smoothing and allow for deeper network and Graph Attention Convolutions \[ [24](https://arxiv.org/html/2409.00829v1#bib.bib24 "")\] followed by aggregation and fully connected layers to generate graph embedding. In order to allow for stochasticity in the generated outputs like in a general GAN setting, we append a noise to the parameter vector of each piece.

Report issue for preceding element

#### 3.2.5 Training Details

Report issue for preceding element

Since the network takes the input in the form of parametric cross-sections, where each cross-section consists of piecewise C1subscript𝐶1C\_{1}italic\_C start\_POSTSUBSCRIPT 1 end\_POSTSUBSCRIPT parametric curves, the parameters of the network become fixed during training if MLPs are used, prohibiting any changes in the number of cross-sections or pieces provided. In order to adapt to the variable nature of our data, we are further motivated to use the graph-based representation by allowing piece-level aggregation and cross-section level aggregation, which allows for a variable number of cross-sections to be provided to the network. Furthermore, we cannot use 1D-convolutions or 2-D convolutions directly in the parametric space because convolutions are not well defined on coefficient spaces.

Report issue for preceding element

We use graph convolutions in both the generator and discriminator. The discriminator is conditioned using the input graph parameters and predicts whether the generated embedding vector is real or fake, the input graph is converted to a graph-level embedding using successive graph convolutions \[ [15](https://arxiv.org/html/2409.00829v1#bib.bib15 "")\] and aggregation. Then the embedding vector is concatenated with the generated embedding and passed to subsequent layers. While the generator consisted of SAGEConv \[ [10](https://arxiv.org/html/2409.00829v1#bib.bib10 "")\] followed by DiffNorm \[ [27](https://arxiv.org/html/2409.00829v1#bib.bib27 "")\] to prevent oversmoothing and allow for deeper network and Graph Attention Convolutions \[ [24](https://arxiv.org/html/2409.00829v1#bib.bib24 "")\] followed by aggregation and fully connected layers to generate graph embedding. In order to allow for stochasticity in the generated outputs like in a general GAN setting, we append a noise to the parameter vector of each piece.

Report issue for preceding element

#### 3.2.6 Training details

Report issue for preceding element

Given a pre-trained autoencoder with encoder E⁢n𝐸𝑛Enitalic\_E italic\_n and decoder D⁢e𝐷𝑒Deitalic\_D italic\_e and a GCN-based generator-discriminator pair {G,D}𝐺𝐷\\{G,D\\}{ italic\_G , italic\_D } we pass a ground truth point cloud Pg⁢tsubscript𝑃𝑔𝑡P\_{gt}italic\_P start\_POSTSUBSCRIPT italic\_g italic\_t end\_POSTSUBSCRIPT containing 2048 points through the encoder to generate an embedding, E⁢n⁢(Pg⁢t)𝐸𝑛subscript𝑃𝑔𝑡En(P\_{gt})italic\_E italic\_n ( italic\_P start\_POSTSUBSCRIPT italic\_g italic\_t end\_POSTSUBSCRIPT ). For a set of input parameterized cross-sections C𝐶Citalic\_C, we create the piece-wise adjacency matrix 𝐀psubscript𝐀𝑝\\mathbf{A}\_{p}bold\_A start\_POSTSUBSCRIPT italic\_p end\_POSTSUBSCRIPT for each cross-section and a cross-section adjacency matrix 𝐀csubscript𝐀𝑐\\mathbf{A}\_{c}bold\_A start\_POSTSUBSCRIPT italic\_c end\_POSTSUBSCRIPT.

Report issue for preceding element

The generator is trained to generate an embedding using the cross-section set C𝐶Citalic\_C and the two adjacency matrices for the point cloud. The generator loss is given by

Report issue for preceding element

|     |     |     |     |
| --- | --- | --- | --- |
|  | ℒG=subscriptℒ𝐺absent\\displaystyle\\mathcal{L}\_{G}=caligraphic\_L start\_POSTSUBSCRIPT italic\_G end\_POSTSUBSCRIPT = | log⁡(1−D⁢(G⁢(C,𝐀p,𝐀c),C,𝐀p,𝐀c))+limit-from1𝐷𝐺𝐶subscript𝐀𝑝subscript𝐀𝑐𝐶subscript𝐀𝑝subscript𝐀𝑐\\displaystyle\\log\\left(1-D\\left(G\\left(C,\\mathbf{A}\_{p},\\mathbf{A}\_{c}\\right),%<br>C,\\mathbf{A}\_{p},\\mathbf{A}\_{c}\\right)\\right)+roman\_log ( 1 - italic\_D ( italic\_G ( italic\_C , bold\_A start\_POSTSUBSCRIPT italic\_p end\_POSTSUBSCRIPT , bold\_A start\_POSTSUBSCRIPT italic\_c end\_POSTSUBSCRIPT ) , italic\_C , bold\_A start\_POSTSUBSCRIPT italic\_p end\_POSTSUBSCRIPT , bold\_A start\_POSTSUBSCRIPT italic\_c end\_POSTSUBSCRIPT ) ) + |  |
|  |  | ℒc⁢h⁢(D⁢e⁢(G⁢(C,𝐀p,𝐀c)),D⁢e⁢(E⁢n⁢(Pg⁢t)))+limit-fromsubscriptℒ𝑐ℎ𝐷𝑒𝐺𝐶subscript𝐀𝑝subscript𝐀𝑐𝐷𝑒𝐸𝑛subscript𝑃𝑔𝑡\\displaystyle\\mathcal{L}\_{ch}\\left(De\\left(G\\left(C,\\mathbf{A}\_{p},\\mathbf{A}\_%<br>{c}\\right)\\right),De\\left(En\\left(P\_{gt}\\right)\\right)\\right)+caligraphic\_L start\_POSTSUBSCRIPT italic\_c italic\_h end\_POSTSUBSCRIPT ( italic\_D italic\_e ( italic\_G ( italic\_C , bold\_A start\_POSTSUBSCRIPT italic\_p end\_POSTSUBSCRIPT , bold\_A start\_POSTSUBSCRIPT italic\_c end\_POSTSUBSCRIPT ) ) , italic\_D italic\_e ( italic\_E italic\_n ( italic\_P start\_POSTSUBSCRIPT italic\_g italic\_t end\_POSTSUBSCRIPT ) ) ) + |  |
|  |  | ℒm⁢s⁢e⁢(G⁢(C,𝐀p,𝐀c),E⁢n⁢(Pg⁢t)),subscriptℒ𝑚𝑠𝑒𝐺𝐶subscript𝐀𝑝subscript𝐀𝑐𝐸𝑛subscript𝑃𝑔𝑡\\displaystyle\\mathcal{L}\_{mse}\\left(G\\left(C,\\mathbf{A}\_{p},\\mathbf{A}\_{c}%<br>\\right),En\\left(P\_{gt}\\right)\\right),caligraphic\_L start\_POSTSUBSCRIPT italic\_m italic\_s italic\_e end\_POSTSUBSCRIPT ( italic\_G ( italic\_C , bold\_A start\_POSTSUBSCRIPT italic\_p end\_POSTSUBSCRIPT , bold\_A start\_POSTSUBSCRIPT italic\_c end\_POSTSUBSCRIPT ) , italic\_E italic\_n ( italic\_P start\_POSTSUBSCRIPT italic\_g italic\_t end\_POSTSUBSCRIPT ) ) , |  |

where ℒc⁢hsubscriptℒ𝑐ℎ\\mathcal{L}\_{ch}caligraphic\_L start\_POSTSUBSCRIPT italic\_c italic\_h end\_POSTSUBSCRIPT is the Chamfer loss between the point clouds generated using the embedding estimated by the generator and the embedding of the ground truth point cloud. ℒm⁢s⁢esubscriptℒ𝑚𝑠𝑒\\mathcal{L}\_{mse}caligraphic\_L start\_POSTSUBSCRIPT italic\_m italic\_s italic\_e end\_POSTSUBSCRIPT is the mean squared error between the embedding estimated by the generator and the embedding of the ground truth point cloud. The discriminator loss can be formulated as

Report issue for preceding element

|     |     |     |     |
| --- | --- | --- | --- |
|  | ℒD=subscriptℒ𝐷absent\\displaystyle\\mathcal{L}\_{D}=caligraphic\_L start\_POSTSUBSCRIPT italic\_D end\_POSTSUBSCRIPT = | (1−log⁡(D⁢(G⁢(C,𝐀p,𝐀c),C,𝐀p,𝐀c)))+limit-from1𝐷𝐺𝐶subscript𝐀𝑝subscript𝐀𝑐𝐶subscript𝐀𝑝subscript𝐀𝑐\\displaystyle\\left(1-\\log\\left(D\\left(G\\left(C,\\mathbf{A}\_{p},\\mathbf{A}\_{c}%<br>\\right),C,\\mathbf{A}\_{p},\\mathbf{A}\_{c}\\right)\\right)\\right)+( 1 - roman\_log ( italic\_D ( italic\_G ( italic\_C , bold\_A start\_POSTSUBSCRIPT italic\_p end\_POSTSUBSCRIPT , bold\_A start\_POSTSUBSCRIPT italic\_c end\_POSTSUBSCRIPT ) , italic\_C , bold\_A start\_POSTSUBSCRIPT italic\_p end\_POSTSUBSCRIPT , bold\_A start\_POSTSUBSCRIPT italic\_c end\_POSTSUBSCRIPT ) ) ) + |  |
|  |  | log⁡(D⁢(E⁢n⁢(Pg⁢t),C,𝐀p,𝐀c)),𝐷𝐸𝑛subscript𝑃𝑔𝑡𝐶subscript𝐀𝑝subscript𝐀𝑐\\displaystyle\\log\\left(D\\left(En\\left(P\_{gt}\\right),C,\\mathbf{A}\_{p},\\mathbf{A%<br>}\_{c}\\right)\\right),roman\_log ( italic\_D ( italic\_E italic\_n ( italic\_P start\_POSTSUBSCRIPT italic\_g italic\_t end\_POSTSUBSCRIPT ) , italic\_C , bold\_A start\_POSTSUBSCRIPT italic\_p end\_POSTSUBSCRIPT , bold\_A start\_POSTSUBSCRIPT italic\_c end\_POSTSUBSCRIPT ) ) , |  |

where the discriminator is conditioned on the input cross-section graph. The generator and discriminator are trained in an adversarial manner (see \[ [9](https://arxiv.org/html/2409.00829v1#bib.bib9 "")\]).

Report issue for preceding element

## 4 Results and Discussion

Report issue for preceding element

We evaluate our approach on different classes of the ShapeNet dataset. We perform an experimental procedure similar to DeepSDF where we divide the models into known shapes, i.e. shapes that were in the training set and testing set referred to as unknown shapes. We test our method in both single-class and multi-class settings. We show some samples for single-class training as well in the supplementary however our key focus is on multi-class training and its analysis.
We perform the training in a multi-class setting. For the multiclass setting, we test on 4 classes - airplane (4K models), chair (6K models), lamp (2K models), and sofa (3K models). Our implementation source code will be made available on Github. We do not perform any class balancing techniques and directly train on the ShapeNet dataset.
We use pytorch geometric \[ [7](https://arxiv.org/html/2409.00829v1#bib.bib7 "")\] for this. We demonstrate the impact of these attentions via an ablative study in the supplementary.

Report issue for preceding element

### 4.1 Cross-section dependence

Report issue for preceding element

We compare the mean Chamfer loss obtained across the different classes for different numbers of input cross-sections (5, 10, 11, 15, 20, and 25) provided as input in Table [1](https://arxiv.org/html/2409.00829v1#S4.T1 "Table 1 ‣ 4.1 Cross-section dependence ‣ 4 Results and Discussion ‣ Curvy: A Parametric Cross-section based Surface Reconstruction"). We observe results for the Chamfer distance obtained after training are shown in Table [1](https://arxiv.org/html/2409.00829v1#S4.T1 "Table 1 ‣ 4.1 Cross-section dependence ‣ 4 Results and Discussion ‣ Curvy: A Parametric Cross-section based Surface Reconstruction"). We observe that the number of cross-sections provided as input has a vital control on the output of the generated point cloud surface, as can be seen from Table [1](https://arxiv.org/html/2409.00829v1#S4.T1 "Table 1 ‣ 4.1 Cross-section dependence ‣ 4 Results and Discussion ‣ Curvy: A Parametric Cross-section based Surface Reconstruction"). We show the results of the proposed model trained on four classes: Airplane, Chair, Lamp, and Sofa with a different number of input parameterized cross-sections in Figure  [4](https://arxiv.org/html/2409.00829v1#S3.F4 "Figure 4 ‣ 3.2.3 Cross-Section Attention ‣ 3.2 Training on parametric space ‣ 3 Approach ‣ Curvy: A Parametric Cross-section based Surface Reconstruction").
The first column displays the ground truth mesh used to sample the ground truth point cloud with cross-sections in red, the second column shows the reconstruction with our method.
We also analyze the variation of cross-sections using Chamfer distance between the generated and ground truth point surfaces as the number of input cross-sections increases/decreases in the supplementary material. We observe a dip in the loss as the number of cross-sections is increased with the eventual flattening of the loss curve (for further discussion and figures, refer to supplementary material).

Report issue for preceding element

Table 1: Per-class Chamfer Distance corresponding to the variation in the number of cross-sections (results for both undersampled and oversampled(>10absent10>10\> 10) cross-sections are shown for a model trained on all aforementioned classes.

| \# cross- | Per-class Chamfer distance | Mean |
| --- | --- | --- |
| sections | Airplane | Chair | Lamp | Sofa |  |
| 2 | 0.4050 | 0.1765 | 2.7306 | 0.3770 | 0.9223 |
| 5 | 0.0493 | 0.0872 | 0.2394 | 0.0772 | 0.1133 |
| 10 | 0.0395 | 0.0829 | 0.0958 | 0.0728 | 0.0728 |
| 11 | 0.0385 | 0.0824 | 0.0927 | 0.0724 | 0.0715 |
| 15 | 0.0378 | 0.0813 | 0.0909 | 0.0715 | 0.0704 |
| 20 | 0.0374 | 0.0807 | 0.0898 | 0.0709 | 0.0697 |
| 25 | 0.0370 | 0.0803 | 0.0896 | 0.0704 | 0.0693 |

Report issue for preceding element

We discuss these trends and perform the t-SNE of the embeddings and demonstrate how the distinguishing capabilities of the network improve further with increasing the number of cross-sections in the supplementary.
However, as in Figure  [4](https://arxiv.org/html/2409.00829v1#S3.F4 "Figure 4 ‣ 3.2.3 Cross-Section Attention ‣ 3.2 Training on parametric space ‣ 3 Approach ‣ Curvy: A Parametric Cross-section based Surface Reconstruction"), despite the sharp reduction in the number of cross-sections, the network still generates a reliable general shape for the class and can distinguish between the classes of parametric forms. In some cases, the failure of reconstruction is much higher depending on the number of samples of a particular shape of the object the network sees and the information in the cross-sections supplied. For example, in Figure  [5](https://arxiv.org/html/2409.00829v1#S4.F5 "Figure 5 ‣ 4.2 Failure Cases ‣ 4 Results and Discussion ‣ Curvy: A Parametric Cross-section based Surface Reconstruction"), in an airplane object, the cross-sections do not contain sufficient information, leading to a completely different object being created, though it is noteworthy that the class of the object reconstructed does seem correct visually.

Report issue for preceding element

### 4.2 Failure Cases

Report issue for preceding element

We observe that in the case of a failure, the network reconstructs a simple object of the class. However, despite it being a failure case, the class of object is still distinguishable by the network. Further, we also notice a deterioration in the samples containing holes, such as chairs and lamps. In Figure  [5](https://arxiv.org/html/2409.00829v1#S4.F5 "Figure 5 ‣ 4.2 Failure Cases ‣ 4 Results and Discussion ‣ Curvy: A Parametric Cross-section based Surface Reconstruction") we can see such samples, the reconstruction is not accurate in the case of airplanes. For example, in the case of the chair, the reconstruction does not accurately maintain the genus of the object for some samples.

Report issue for preceding element

| Ground Truth | Predicted |
| --- | --- |
| ![Refer to caption](https://arxiv.org/html/2409.00829v1/) | ![Refer to caption](https://arxiv.org/html/2409.00829v1/) |
| ![Refer to caption](https://arxiv.org/html/2409.00829v1/) | ![Refer to caption](https://arxiv.org/html/2409.00829v1/) |

Figure 5: Failure cases resulting in incorrect shapes. Input to the network are the cross-sections (red) belonging to the ground truth mesh(white).Report issue for preceding element

## 5 Comparisons

Report issue for preceding element

We compare our method against 4 methods:
VIPSS method for variational surface reconstruction from cross-sections \[ [13](https://arxiv.org/html/2409.00829v1#bib.bib13 "")\],
surface reconstruction from non-parallel curve networks \[ [18](https://arxiv.org/html/2409.00829v1#bib.bib18 "")\], a state of the art deep learning based method P2P-Net \[ [26](https://arxiv.org/html/2409.00829v1#bib.bib26 "")\] and the recent ORex \[ [21](https://arxiv.org/html/2409.00829v1#bib.bib21 "")\] and show results in Figure  [6](https://arxiv.org/html/2409.00829v1#S6.F6 "Figure 6 ‣ 6 Conclusion and Future Scope ‣ Curvy: A Parametric Cross-section based Surface Reconstruction").
Most of these methods suffer from holes and instabilities for sparse cross-sections; therefore, to be fair, we sample more cross-sections in those cases. However, we restrict our method to 10 cross-sections. VIPSS, ORex, and Liu’s methods require careful sampling and sometimes tend to fail randomly for sparse cross-sections. We show the best-case results for these methods.
VIPSS is very sensitive to λ𝜆\\lambdaitalic\_λ and requires a large number ∼80similar-toabsent80\\sim 80∼ 80 of cross-sections for faithful reconstruction due to failure due to openness in cross-sections; however, we still notice artifacts.
We checked the reconstruction with the method proposed in \[ [18](https://arxiv.org/html/2409.00829v1#bib.bib18 "")\], however, the available implementation discards many cross-sections that lead to incorrect results.
We show results for the cases where we did not observe this issue for a fair comparison. For Orex \[ [21](https://arxiv.org/html/2409.00829v1#bib.bib21 "")\] as well, we observe that it performs really well when cross-sections are dense; however, it fails in the case of sparse cross-sections. Therefore, for some samples, we show results in cases where it performs reasonably well.

Report issue for preceding element

We further compare our method against a state-of-the-art deep learning-based method called P2P-Net. We modify P2P Net and train it on points sampled from our cross-sections. We notice that in some cases, despite performing better in terms of metrics, there are still completion issues in several samples, such as the chair shown in Figure  [6](https://arxiv.org/html/2409.00829v1#S6.F6 "Figure 6 ‣ 6 Conclusion and Future Scope ‣ Curvy: A Parametric Cross-section based Surface Reconstruction").
Our method generates symmetric structures leading to higher loss value but better perception quality and semantically correct different structures such as the right-hand rest of the sofa and missing leg in the chair.
This also highlights a weakness of our method pertaining to the lack of strict adherence to the cross-sections since our method relies on embedding decoded by the pre-trained decoder. However, we believe that can be circumvented by better pre-training schemes since the performance of the pre-trained decoder forms the lower bound of the reconstruction error and can be swapped with any of the better-performing point cloud generators.

Report issue for preceding element

In order to visualize the error in reconstruction from our method and P2P-Net, we perform surface meshing of our resulting point cloud with Poisson Reconstruction \[ [14](https://arxiv.org/html/2409.00829v1#bib.bib14 "")\]
, by computing normals from the ground truth mesh for the best-case-scenario. For VIPSS, we also modified the method and provided normals from the GT mesh. We show similar histograms for the surfaces obtained from other methods.
We also note the Hausdorff distance (dHsubscript𝑑𝐻d\_{H}italic\_d start\_POSTSUBSCRIPT italic\_H end\_POSTSUBSCRIPT) obtained for different methods in Figure  [6](https://arxiv.org/html/2409.00829v1#S6.F6 "Figure 6 ‣ 6 Conclusion and Future Scope ‣ Curvy: A Parametric Cross-section based Surface Reconstruction").
We notice that during the generation of the point cloud, since our method does not have hard constraints for precise overlap with input, the shift in point cloud can lead to a relative rise in the Hausdorff distance, as can be seen in the case of the chair in Figure  [6](https://arxiv.org/html/2409.00829v1#S6.F6 "Figure 6 ‣ 6 Conclusion and Future Scope ‣ Curvy: A Parametric Cross-section based Surface Reconstruction"). However, it outperforms the other methods in both qualitative and quantitative comparisons in several cases.

Report issue for preceding element

## 6 Conclusion and Future Scope

Report issue for preceding element

With this work, we open a new direction for the exciting domain of cross-section-based reconstruction. We generate a new dataset that can be used for multiple tasks. The ability to use parametric cross-sections directly in a learning-based setting exempts the use of any sampling-based restrictions in deep learning-based methods.
The complete information of the curve is encapsulated in the coefficients of the parametric representation. Further, we utilize GCNs at scale and demonstrate their effectiveness for parametric curves and the ability of the GCNs to capture neighborhood information, which helps deduce better relationships among the cross-sections using attention, adding to the explainability with the flexibility to use any models trained on point cloud generation. We show empirical evidence to analyze the changes in reconstruction, both in terms of the embedding space representation and point cloud reconstruction, to understand the changes with respect to the variation in the amount of information provided to the network. This builds a strong motivation and opens up the field to further research such as the disentanglement of latent features and information-theoretic aspect of cross-section-based reconstruction which we hope to cover in future works.

Report issue for preceding element

| GT Mesh + Input<br>Report issue for preceding element | ![Refer to caption](https://arxiv.org/html/2409.00829v1/) | ![Refer to caption](https://arxiv.org/html/2409.00829v1/) | ![Refer to caption](https://arxiv.org/html/2409.00829v1/) |
| VIPSS\[ [13](https://arxiv.org/html/2409.00829v1#bib.bib13 "")\]<br>Report issue for preceding element | ![Refer to caption](https://arxiv.org/html/2409.00829v1/extracted/5826454/images/inset_images/airplane/plane_heatmaps_vipss_crop.jpg)![Refer to caption](https://arxiv.org/html/2409.00829v1/)Report issue for preceding element | ![Refer to caption](https://arxiv.org/html/2409.00829v1/extracted/5826454/images/inset_images/chair/chair_heatmaps_vipss_crop.jpg)![Refer to caption](https://arxiv.org/html/2409.00829v1/)Report issue for preceding element | ![Refer to caption](https://arxiv.org/html/2409.00829v1/extracted/5826454/images/inset_images/sofa/same_orientation/vipss_heatmap_crop.jpg)![Refer to caption](https://arxiv.org/html/2409.00829v1/)Report issue for preceding element |
|  | dH:0.032574:subscript𝑑𝐻0.032574d\_{H}:0.032574italic\_d start\_POSTSUBSCRIPT italic\_H end\_POSTSUBSCRIPT : 0.032574 | dH:0.056161:subscript𝑑𝐻0.056161d\_{H}:0.056161italic\_d start\_POSTSUBSCRIPT italic\_H end\_POSTSUBSCRIPT : 0.056161 | dH:0.001533:subscript𝑑𝐻0.001533d\_{H}:0.001533italic\_d start\_POSTSUBSCRIPT italic\_H end\_POSTSUBSCRIPT : 0.001533 |
| Liu et. al\[ [18](https://arxiv.org/html/2409.00829v1#bib.bib18 "")\]<br>Report issue for preceding element | ![Refer to caption](https://arxiv.org/html/2409.00829v1/extracted/5826454/images/inset_images/airplane/plane_heatmaps_liu_crop.jpg)![Refer to caption](https://arxiv.org/html/2409.00829v1/)Report issue for preceding element | ![Refer to caption](https://arxiv.org/html/2409.00829v1/extracted/5826454/images/inset_images/chair/chair_heatmaps_liu_crop.jpg)![Refer to caption](https://arxiv.org/html/2409.00829v1/)Report issue for preceding element | ![Refer to caption](https://arxiv.org/html/2409.00829v1/extracted/5826454/images/inset_images/sofa/same_orientation/liu_heatmap.jpg)![Refer to caption](https://arxiv.org/html/2409.00829v1/)Report issue for preceding element |
|  | dH:0.005765:subscript𝑑𝐻0.005765d\_{H}:0.005765italic\_d start\_POSTSUBSCRIPT italic\_H end\_POSTSUBSCRIPT : 0.005765 | dH:0.039835:subscript𝑑𝐻0.039835d\_{H}:0.039835italic\_d start\_POSTSUBSCRIPT italic\_H end\_POSTSUBSCRIPT : 0.039835 | dH:0.010035:subscript𝑑𝐻0.010035d\_{H}:0.010035italic\_d start\_POSTSUBSCRIPT italic\_H end\_POSTSUBSCRIPT : 0.010035 |
| P2P Net\[ [26](https://arxiv.org/html/2409.00829v1#bib.bib26 "")\]<br>Report issue for preceding element | ![Refer to caption](https://arxiv.org/html/2409.00829v1/extracted/5826454/images/inset_images/airplane/plane_heatmaps_p2p_crop.jpg)![Refer to caption](https://arxiv.org/html/2409.00829v1/)Report issue for preceding element | ![Refer to caption](https://arxiv.org/html/2409.00829v1/extracted/5826454/images/inset_images/chair/chair_heatmaps_p2p_crop.jpg)![Refer to caption](https://arxiv.org/html/2409.00829v1/)Report issue for preceding element | ![Refer to caption](https://arxiv.org/html/2409.00829v1/extracted/5826454/images/inset_images/sofa/same_orientation/p2p_heatmap_crop.jpg)![Refer to caption](https://arxiv.org/html/2409.00829v1/)Report issue for preceding element |
|  | dH:0.023185:subscript𝑑𝐻0.023185d\_{H}:0.023185italic\_d start\_POSTSUBSCRIPT italic\_H end\_POSTSUBSCRIPT : 0.023185 | dH:0.032854:subscript𝑑𝐻0.032854d\_{H}:0.032854italic\_d start\_POSTSUBSCRIPT italic\_H end\_POSTSUBSCRIPT : 0.032854 | dH:0.012473:subscript𝑑𝐻0.012473d\_{H}:0.012473italic\_d start\_POSTSUBSCRIPT italic\_H end\_POSTSUBSCRIPT : 0.012473 |
| ORex\[ [21](https://arxiv.org/html/2409.00829v1#bib.bib21 "")\]<br>Report issue for preceding element | ![Refer to caption](https://arxiv.org/html/2409.00829v1/extracted/5826454/images/inset_images/airplane/orex/orex_new_recons_heatmap01_new.jpg)![Refer to caption](https://arxiv.org/html/2409.00829v1/)Report issue for preceding element | ![Refer to caption](https://arxiv.org/html/2409.00829v1/extracted/5826454/images/inset_images/chair/orex/chair_recons_heatmap01.jpg)![Refer to caption](https://arxiv.org/html/2409.00829v1/)Report issue for preceding element | ![Refer to caption](https://arxiv.org/html/2409.00829v1/extracted/5826454/images/inset_images/sofa/orex_new_recons_heatmap02.jpg)![Refer to caption](https://arxiv.org/html/2409.00829v1/)Report issue for preceding element |
|  | dH:0.022027:subscript𝑑𝐻0.022027d\_{H}:0.022027italic\_d start\_POSTSUBSCRIPT italic\_H end\_POSTSUBSCRIPT : 0.022027 | dH:0.049031:subscript𝑑𝐻0.049031d\_{H}:0.049031italic\_d start\_POSTSUBSCRIPT italic\_H end\_POSTSUBSCRIPT : 0.049031 | dH:0.015033:subscript𝑑𝐻0.015033d\_{H}:0.015033italic\_d start\_POSTSUBSCRIPT italic\_H end\_POSTSUBSCRIPT : 0.015033 |
| Ours<br>Report issue for preceding element | ![Refer to caption](https://arxiv.org/html/2409.00829v1/extracted/5826454/images/inset_images/airplane/plane_heatmaps_gcn_crop.jpg)![Refer to caption](https://arxiv.org/html/2409.00829v1/)Report issue for preceding element | ![Refer to caption](https://arxiv.org/html/2409.00829v1/extracted/5826454/images/inset_images/chair/chair_heatmaps_gcn_crop.jpg)![Refer to caption](https://arxiv.org/html/2409.00829v1/)Report issue for preceding element | ![Refer to caption](https://arxiv.org/html/2409.00829v1/extracted/5826454/images/inset_images/sofa/sofa_heatmap_gcn.jpg)![Refer to caption](https://arxiv.org/html/2409.00829v1/)Report issue for preceding element |
|  | dH:0.032111:subscript𝑑𝐻0.032111d\_{H}:0.032111italic\_d start\_POSTSUBSCRIPT italic\_H end\_POSTSUBSCRIPT : 0.032111 | dH:0.049031:subscript𝑑𝐻0.049031d\_{H}:0.049031italic\_d start\_POSTSUBSCRIPT italic\_H end\_POSTSUBSCRIPT : 0.049031 | dH:0.019826:subscript𝑑𝐻0.019826d\_{H}:0.019826italic\_d start\_POSTSUBSCRIPT italic\_H end\_POSTSUBSCRIPT : 0.019826 |

Figure 6: Comparison with the state-of-the-art methods. Inset shows point-wise surface error compared with the GT.Report issue for preceding element

## References

Report issue for preceding element

- \[1\]↑
Panos Achlioptas, Olga Diamanti, Ioannis Mitliagkas, and Leonidas Guibas.
Learning representations and generative models for 3D point clouds.
In International conference on machine learning, pages 40–49. PMLR, 2018.

- \[2\]↑
Matan Atzmon and Yaron Lipman.
Sal: Sign agnostic learning of shapes from raw data.
In Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition, pages 2565–2574, 2020.

- \[3\]↑
Jean-Daniel Boissonnat and Pooran Memari.
Shape reconstruction from unorganized cross-sections.
In Symposium on geometry processing, pages 89–98. Citeseer, 2007.

- \[4\]↑
Angel X Chang, Thomas Funkhouser, Leonidas Guibas, Pat Hanrahan, Qixing Huang, Zimo Li, Silvio Savarese, Manolis Savva, Shuran Song, Hao Su, et al.
ShapeNet: An information-rich 3D model repository.
arXiv preprint arXiv:1512.03012, 2015.

- \[5\]↑
David H Douglas and Thomas K Peucker.
Algorithms for the reduction of the number of points required to represent a digitized line or its caricature.
Cartographica: the international journal for geographic information and geovisualization, 10(2):112–122, 1973.

- \[6\]↑
Haoqiang Fan, Hao Su, and Leonidas J Guibas.
A point set generation network for 3D object reconstruction from a single image.
In Proceedings of the IEEE conference on computer vision and pattern recognition, pages 605–613, 2017.

- \[7\]↑
Matthias Fey and Jan E. Lenssen.
Fast graph representation learning with PyTorch Geometric.
In ICLR Workshop on Representation Learning on Graphs and Manifolds, 2019.

- \[8\]↑
Matheus Gadelha, Rui Wang, and Subhransu Maji.
Multiresolution tree networks for 3D point cloud processing.
In Proceedings of the European Conference on Computer Vision (ECCV), pages 103–118, 2018.

- \[9\]↑
Ian Goodfellow, Jean Pouget-Abadie, Mehdi Mirza, Bing Xu, David Warde-Farley, Sherjil Ozair, Aaron Courville, and Yoshua Bengio.
Generative adversarial networks.
Communications of the ACM, 63(11):139–144, 2020.

- \[10\]↑
William L Hamilton, Rex Ying, and Jure Leskovec.
Inductive representation learning on large graphs.
In Proceedings of the 31st International Conference on Neural Information Processing Systems, pages 1025–1035, 2017.

- \[11\]↑
Zhizhong Han, Xiyang Wang, Yu-Shen Liu, and Matthias Zwicker.
Multi-angle point cloud-VAE: Unsupervised feature learning for 3D point clouds from multiple angles by joint self-reconstruction and half-to-half prediction.
In 2019 IEEE/CVF International Conference on Computer Vision (ICCV), pages 10441–10450. IEEE, 2019.

- \[12\]↑
J Huang and C.H Menq.
Combinatorial manifold mesh reconstruction and optimization from unorganized points with arbitrary topology.
Computer-Aided Design, 34(2):149–165, 2002.

- \[13\]↑
Zhiyang Huang, Nathan Carr, and Tao Ju.
Variational implicit point set surfaces.
ACM Transactions on Graphics (TOG), 38(4):1–13, 2019.

- \[14\]↑
M. Kazhdan, M. Bolitho, and H. Hoppe.
Poisson surface reconstruction.
In Eurographics, 2006.

- \[15\]↑
Thomas N. Kipf and Max Welling.
Semi-supervised classification with graph convolutional networks.
In 5th International Conference on Learning Representations, ICLR 2017, 2017.

- \[16\]↑
Roee Lazar, Nadav Dym, Yam Kushinsky, Zhiyang Huang, Tao Ju, and Yaron Lipman.
Robust optimization for topological surface reconstruction.
ACM Transactions on Graphics (TOG), 37(4):1–10, 2018.

- \[17\]↑
Chen-Hsuan Lin, Chen Kong, and Simon Lucey.
Learning efficient point cloud generation for dense 3D object reconstruction.
In proceedings of the AAAI Conference on Artificial Intelligence, volume 32, 2018.

- \[18\]↑
Lu Liu, Chandrajit Bajaj, Joseph O Deasy, Daniel A Low, and Tao Ju.
Surface reconstruction from non-parallel curve networks.
In Computer Graphics Forum, volume 27, pages 155–163. Wiley Online Library, 2008.

- \[19\]↑
Pooran Memari and Jean-Daniel Boissonnat.
Provably good 2D shape reconstruction from unorganized cross-sections.
In Computer Graphics Forum, volume 27, pages 1403–1410. Wiley Online Library, 2008.

- \[20\]↑
Muhammad Sarmad, Hyunjoo Jenny Lee, and Young Min Kim.
RL-GAN-Net: A reinforcement learning agent controlled gan network for real-time point cloud shape completion.
In Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition, pages 5898–5907, 2019.

- \[21\]↑
Haim Sawdayee, Amir Vaxman, and Amit H Bermano.
Orex: Object reconstruction from planner cross-sections using neural fields.
arXiv preprint arXiv:2211.12886, 2022.

- \[22\]↑
Ojaswa Sharma and Nidhi Agarwal.
Signed distance based 3D surface reconstruction from unorganized planar cross-sections.
Computers & Graphics, 62:67–76, 2017.

- \[23\]↑
Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N Gomez, Łukasz Kaiser, and Illia Polosukhin.
Attention is all you need.
In Advances in neural information processing systems, pages 5998–6008, 2017.

- \[24\]↑
Petar Velickovic, Guillem Cucurull, Arantxa Casanova, Adriana Romero, Pietro Liò, and Yoshua Bengio.
Graph attention networks.
In 6th International Conference on Learning Representations, ICLR 2018, 2018.

- \[25\]↑
Xin Wen, Tianyang Li, Zhizhong Han, and Yu-Shen Liu.
Point cloud completion by skip-attention network with hierarchical folding.
In Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition, pages 1939–1948, 2020.

- \[26\]↑
Kangxue Yin, Hui Huang, Daniel Cohen-Or, and Hao Zhang.
P2p-net: Bidirectional point displacement net for shape transform.
ACM Transactions on Graphics (TOG), 37(4):1–13, 2018.

- \[27\]↑
Kaixiong Zhou, Xiao Huang, Yuening Li, Daochen Zha, Rui Chen, and Xia Hu.
Towards deeper graph neural networks with differentiable group normalization.
Advances in Neural Information Processing Systems, 33:4917–4928, 2020.

- \[28\]↑
Ming Zou, Michelle Holloway, Nathan Carr, and Tao Ju.
Topology-constrained surface reconstruction from cross-sections.
ACM Transactions on Graphics (TOG), 34(4):1–10, 2015.


Report Issue

##### Report GitHub Issue

Title:

Content selection saved. Describe the issue below:

Description:

Submit without GitHubSubmit in GitHub

Report Issue for Selection

Generated by
[L\\
A\\
T\\
Exml![[LOGO]](<Base64-Image-Removed>)](https://math.nist.gov/~BMiller/LaTeXML/)

## Instructions for reporting errors

We are continuing to improve HTML versions of papers, and your feedback helps enhance accessibility and mobile support. To report errors in the HTML that will help us improve conversion and rendering, choose any of the methods listed below:

- Click the "Report Issue" button.
- Open a report feedback form via keyboard, use " **Ctrl + ?**".
- Make a text selection and click the "Report Issue for Selection" button near your cursor.
- You can use Alt+Y to toggle on and Alt+Shift+Y to toggle off accessible reporting links at each section.

Our team has already identified [the following issues](https://github.com/arXiv/html_feedback/issues). We appreciate your time reviewing and reporting rendering errors we may not have found yet. Your efforts will help us improve the HTML versions for all readers, because disability should not be a barrier to accessing research. Thank you for your continued support in championing open access for all.

Have a free development cycle? Help support accessibility at arXiv! Our collaborators at LaTeXML maintain a [list of packages that need conversion](https://github.com/brucemiller/LaTeXML/wiki/Porting-LaTeX-packages-for-LaTeXML), and welcome [developer contributions](https://github.com/brucemiller/LaTeXML/issues).