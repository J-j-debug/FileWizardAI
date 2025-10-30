import { Component, Input } from '@angular/core';
import { HttpParams } from "@angular/common/http";
import { DataService } from "../data.service";

@Component({
  selector: 'app-search-files',
  template: `
    <mat-form-field class="example-full-width">
      <mat-label>Search text</mat-label>
      <textarea matInput placeholder="Ask a question about your documents" [(ngModel)]="searchQuery"></textarea>
    </mat-form-field>
    <button mat-raised-button (click)="searchFiles()" style="margin-left: 1%">Search</button>
    <div class="spinner-container" *ngIf="isLoading">
        <mat-spinner></mat-spinner>
    </div>
    <div *ngIf="ragResult" class="results-container">
      <h3>Response:</h3>
      <p>{{ ragResult.response }}</p>

      <h4>Sources:</h4>
      <ul>
        <li *ngFor="let source of ragResult.sources">{{ source }}</li>
      </ul>
    </div>
  `,
  styles: [`
    .example-full-width {
      width: 100%;
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
  `]
})
export class SearchFilesComponent {
  searchQuery: string = "";
  ragResult: any;
  isLoading: boolean = false;
  @Input() rootPath: string = "";
  @Input() isRecursive: boolean = false;
  @Input() filesExts: string[] = [];

  constructor(private dataService: DataService) {
  }

  searchFiles(): void {
    this.ragResult = null;
    this.isLoading = true;
    let params = new HttpParams();
    params = params.set("query", this.searchQuery);
    this.dataService
      .ragSearch(params)
      .subscribe((data: any) => {
        this.ragResult = data;
        this.isLoading = false;
      })
  }
}
