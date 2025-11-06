import { Component, Input } from '@angular/core';
import { HttpParams } from "@angular/common/http";
import { DataService } from "../data.service";

@Component({
  selector: 'app-search-files',
  template: `
    <div class="search-controls">
      <mat-form-field class="search-input">
        <mat-label>Search text</mat-label>
        <textarea matInput placeholder="Ask a question about your documents" [(ngModel)]="searchQuery"></textarea>
      </mat-form-field>
      <mat-form-field class="collection-select">
        <mat-label>Search In</mat-label>
        <mat-select [(ngModel)]="selectedCollection">
          <mat-option *ngFor="let collection of collections" [value]="collection.value">
            {{ collection.viewValue }}
          </mat-option>
        </mat-select>
      </mat-form-field>
      <mat-form-field class="top-k-input">
        <mat-label>Top K</mat-label>
        <input matInput type="number" [(ngModel)]="topK" min="1" max="20">
      </mat-form-field>
      <button mat-raised-button (click)="searchFiles()" class="search-button">Search</button>
    </div>
    <div class="spinner-container" *ngIf="isLoading">
        <mat-spinner></mat-spinner>
    </div>
    <div *ngIf="ragResult" class="results-container">
      <h3>Réponse Principale:</h3>
      <p>{{ ragResult.main_response.response }}</p>
      <div *ngIf="ragResult.main_response.source" class="source-citation">
        <strong>Source:</strong>
        <a [href]="'http://localhost:8000/download?encoded_path=' + encodeFilePath(ragResult.main_response.source.file_path)" target="_blank">
          {{ ragResult.main_response.source.file_path }}
        </a>
        (Page: {{ ragResult.main_response.source.page_number }})
      </div>

      <h4>Autres Passages Pertinents:</h4>
      <ul *ngIf="ragResult.other_relevant_passages && ragResult.other_relevant_passages.length > 0; else noOtherPassages">
        <li *ngFor="let passage of ragResult.other_relevant_passages">
          <p class="passage-content">"{{ passage.document }}"</p>
          <div class="source-citation">
            <strong>Source:</strong>
            <a [href]="'http://localhost:8000/download?encoded_path=' + encodeFilePath(passage.metadata.file_path)" target="_blank">
              {{ passage.metadata.file_path }}
            </a>
            (Page: {{ passage.metadata.page_number }})
          </div>
        </li>
      </ul>
      <ng-template #noOtherPassages>
        <p>Aucun autre passage pertinent trouvé.</p>
      </ng-template>
    </div>
  `,
  styles: [`
    .search-controls {
      display: flex;
      align-items: center;
      gap: 1rem;
      width: 100%;
    }
    .search-input {
      flex-grow: 1;
    }
    .collection-select {
      width: 250px; /* Adjust as needed */
    }
    .top-k-input {
      width: 80px;
    }
    .spinner-container {
      display: flex;
      justify-content: center;
      align-items: center;
      margin-top: 20px;
    }
    .results-container {
      margin-top: 20px;
    }
    .passage-content {
      font-style: italic;
      padding-left: 1rem;
      border-left: 2px solid #ccc;
    }
    .source-citation {
      font-size: 0.9em;
      color: #555;
    }
  `]
})
export class SearchFilesComponent {
  searchQuery: string = "";
  ragResult: any;
  isLoading: boolean = false;
  selectedCollection: string = "file_embeddings"; // Default collection
  topK: number = 5;
  collections = [
    { value: "file_embeddings", viewValue: "Recherche Standard" },
    { value: "file_embeddings_unstructured", viewValue: "Recherche Avancée (Unstructured)" }
  ];
  @Input() rootPath: string = "";
  @Input() isRecursive: boolean = false;
  @Input() filesExts: string[] = [];

  constructor(private dataService: DataService) {
  }

  encodeFilePath(path: string): string {
    return btoa(path);
  }

  searchFiles(): void {
    this.ragResult = null;
    this.isLoading = true;
    let params = new HttpParams();
    params = params.set("query", this.searchQuery);
    params = params.set("collection_name", this.selectedCollection);
    params = params.set("top_k", this.topK.toString());
    this.dataService
      .ragSearch(params)
      .subscribe((data: any) => {
        this.ragResult = data;
        this.isLoading = false;
      })
  }
}
